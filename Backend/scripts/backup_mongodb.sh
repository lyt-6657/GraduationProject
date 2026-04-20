#!/bin/bash

# MongoDB 备份脚本
# 该脚本用于定期备份 MongoDB 数据库

# 配置参数
MONGODB_HOST=${MONGODB_HOST:-localhost}
MONGODB_PORT=${MONGODB_PORT:-27017}
MONGODB_USERNAME=${MONGODB_USERNAME}
MONGODB_PASSWORD=${MONGODB_PASSWORD}
MONGODB_DB_NAME=${MONGODB_DB_NAME:-graduation_project}

# 备份目录
BACKUP_DIR=${BACKUP_DIR:-"$(pwd)/mongodb_backups"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${BACKUP_DIR}/${MONGODB_DB_NAME}_${TIMESTAMP}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 构建 mongodump 命令
if [ -n "${MONGODB_USERNAME}" ] && [ -n "${MONGODB_PASSWORD}" ]; then
    MONGODUMP_CMD="mongodump --host ${MONGODB_HOST} --port ${MONGODB_PORT} --username ${MONGODB_USERNAME} --password ${MONGODB_PASSWORD} --authenticationDatabase admin --db ${MONGODB_DB_NAME} --out ${BACKUP_PATH}"
else
    MONGODUMP_CMD="mongodump --host ${MONGODB_HOST} --port ${MONGODB_PORT} --db ${MONGODB_DB_NAME} --out ${BACKUP_PATH}"
fi

# 执行备份
echo "开始备份 MongoDB 数据库 ${MONGODB_DB_NAME}..."
echo "执行命令: ${MONGODUMP_CMD}"

# 运行备份命令
${MONGODUMP_CMD}

# 检查备份结果
if [ $? -eq 0 ]; then
    echo "备份成功! 备份文件保存在: ${BACKUP_PATH}"
    
    # 压缩备份文件
    echo "正在压缩备份文件..."
    tar -czf "${BACKUP_PATH}.tar.gz" -C "${BACKUP_DIR}" "${MONGODB_DB_NAME}_${TIMESTAMP}"
    
    # 删除未压缩的备份目录
    rm -rf "${BACKUP_PATH}"
    
    echo "备份文件已压缩: ${BACKUP_PATH}.tar.gz"
    
    # 清理旧备份（保留最近7天的备份）
    echo "清理7天前的备份文件..."
    find "${BACKUP_DIR}" -name "${MONGODB_DB_NAME}_*.tar.gz" -mtime +7 -delete
    
    echo "备份完成!"
else
    echo "备份失败!"
    exit 1
fi
