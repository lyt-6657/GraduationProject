import logging
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

# 使用专门的监控日志记录器
logger = logging.getLogger("monitoring")


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        """初始化告警管理器"""
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_thresholds = {
            "error_rate": 0.1,  # 错误率阈值
            "response_time": 5.0,  # 响应时间阈值（秒）
            "service_down": True,  # 服务宕机阈值
        }
    
    def check_alert(self, alert_type: str, value: Any) -> bool:
        """
        检查是否触发告警
        
        Args:
            alert_type: 告警类型
            value: 告警值
            
        Returns:
            bool: 是否触发告警
        """
        if alert_type not in self.alert_thresholds:
            return False
        
        threshold = self.alert_thresholds[alert_type]
        
        if alert_type == "error_rate":
            return value > threshold
        elif alert_type == "response_time":
            return value > threshold
        elif alert_type == "service_down":
            return value == threshold
        
        return False
    
    def send_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        发送告警
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            details: 告警详情
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 记录告警
            alert_id = f"{alert_type}_{int(time.time())}"
            self.alerts[alert_id] = {
                "type": alert_type,
                "message": message,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            }
            
            # 打印告警信息（实际生产环境中可以发送邮件、短信等）
            logger.warning(f"[ALERT] {alert_type}: {message}")
            if details:
                logger.warning(f"[ALERT DETAILS] {details}")
            
            # 这里可以添加实际的告警发送逻辑，如发送邮件、短信等
            # self._send_email_alert(alert_type, message, details)
            
            return True
        except Exception as e:
            logger.error(f"发送告警失败: {e}")
            return False
    
    def _send_email_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        发送邮件告警
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            details: 告警详情
            
        Returns:
            bool: 是否发送成功
        """
        # 这里需要配置邮件服务器信息
        # 实际生产环境中需要填写真实的邮件服务器配置
        smtp_server = "smtp.example.com"
        smtp_port = 587
        smtp_user = "alert@example.com"
        smtp_password = "password"
        recipient = "admin@example.com"
        
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = recipient
            msg["Subject"] = f"[告警] {alert_type}"
            
            body = f"告警类型: {alert_type}\n告警消息: {message}\n"
            if details:
                body += f"告警详情: {details}\n"
            body += f"告警时间: {datetime.now().isoformat()}"
            
            msg.attach(MIMEText(body, "plain"))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")
            return False
    
    def get_alerts(self, limit: int = 100) -> list:
        """
        获取告警列表
        
        Args:
            limit: 返回的告警数量限制
            
        Returns:
            list: 告警列表
        """
        alerts = list(self.alerts.values())
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        return alerts[:limit]


class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self):
        """初始化服务监控器"""
        self.alert_manager = AlertManager()
        self.request_metrics = {
            "total": 0,
            "success": 0,
            "error": 0,
            "response_times": []
        }
        self.last_check_time = time.time()
    
    def record_request(self, success: bool, response_time: float) -> None:
        """
        记录请求
        
        Args:
            success: 是否成功
            response_time: 响应时间（秒）
        """
        self.request_metrics["total"] += 1
        if success:
            self.request_metrics["success"] += 1
        else:
            self.request_metrics["error"] += 1
        
        # 只保留最近 100 个响应时间
        self.request_metrics["response_times"].append(response_time)
        if len(self.request_metrics["response_times"]) > 100:
            self.request_metrics["response_times"].pop(0)
    
    def check_service_health(self) -> Dict[str, Any]:
        """
        检查服务健康状态
        
        Returns:
            Dict[str, Any]: 健康状态
        """
        current_time = time.time()
        
        # 计算错误率
        if self.request_metrics["total"] > 0:
            error_rate = self.request_metrics["error"] / self.request_metrics["total"]
        else:
            error_rate = 0
        
        # 计算平均响应时间
        if self.request_metrics["response_times"]:
            avg_response_time = sum(self.request_metrics["response_times"]) / len(self.request_metrics["response_times"])
        else:
            avg_response_time = 0
        
        # 检查是否触发告警
        if self.alert_manager.check_alert("error_rate", error_rate):
            self.alert_manager.send_alert(
                "error_rate",
                f"错误率过高: {error_rate:.2f}",
                {
                    "total_requests": self.request_metrics["total"],
                    "error_requests": self.request_metrics["error"],
                    "success_requests": self.request_metrics["success"]
                }
            )
        
        if self.alert_manager.check_alert("response_time", avg_response_time):
            self.alert_manager.send_alert(
                "response_time",
                f"响应时间过长: {avg_response_time:.2f}s",
                {
                    "average_response_time": avg_response_time,
                    "max_response_time": max(self.request_metrics["response_times"]) if self.request_metrics["response_times"] else 0,
                    "min_response_time": min(self.request_metrics["response_times"]) if self.request_metrics["response_times"] else 0
                }
            )
        
        # 重置 metrics（每 5 分钟）
        if current_time - self.last_check_time > 300:
            self.request_metrics = {
                "total": 0,
                "success": 0,
                "error": 0,
                "response_times": []
            }
            self.last_check_time = current_time
        
        return {
            "error_rate": error_rate,
            "average_response_time": avg_response_time,
            "total_requests": self.request_metrics["total"],
            "error_requests": self.request_metrics["error"],
            "success_requests": self.request_metrics["success"]
        }


# 全局监控实例
monitor = ServiceMonitor()
