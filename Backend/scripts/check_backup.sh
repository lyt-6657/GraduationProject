#!/bin/bash
"""
检测 MongoDB 备份功能是否正常
"""

# 备份目录
BACKUP_DIR="./backups"

# 日志文件
LOG_FILE="./logs/backup_check.log"

# 当前时间
CURRENT_TIME=$(date +"%Y-%m-%d %H:%M:%S")

# 检查备份目录是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    echo "[$CURRENT_TIME] 错误: 备份目录不存在"
    exit 1
fi

# 检查最近的备份文件
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "*.gz" -type f | sort -r | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "[$CURRENT_TIME] 错误: 没有找到备份文件"
    exit 1
fi

# 检查备份文件大小
BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)

# 检查备份文件是否完整（尝试解压）
tar -tzf "$LATEST_BACKUP" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[$CURRENT_TIME] 错误: 备份文件损坏"
    exit 1
fi

# 检查备份文件的修改时间
BACKUP_TIME=$(stat -c "%y" "$LATEST_BACKUP" 2>/dev/null || stat -f "%Sm" "$LATEST_BACKUP")

# 输出检测结果
echo "[$CURRENT_TIME] 备份检测结果:"
echo "- 最新备份文件: $LATEST_BACKUP"
echo "- 备份文件大小: $BACKUP_SIZE"
echo "- 备份时间: $BACKUP_TIME"
echo "- 备份文件状态: 完整"
echo "- 备份功能: 正常"

exit 0
