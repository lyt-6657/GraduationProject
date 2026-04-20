# MongoDB 备份与恢复指南

## 1. 定时备份配置

### Linux 系统 (使用 crontab)

1. **编辑 crontab 配置文件**:
   ```bash
   crontab -e
   ```

2. **添加以下定时任务**:
   ```bash
   # 每周一次小型备份（每周日凌晨 2:00）
   0 2 * * 0 /bin/bash /path/to/backend/scripts/backup_mongodb.sh --type incremental >> /path/to/backend/logs/backup.log 2>&1

   # 每月一次完整备份（每月 1 日凌晨 3:00）
   0 3 1 * * /bin/bash /path/to/backend/scripts/backup_mongodb.sh --type full >> /path/to/backend/logs/backup.log 2>&1

   # 每四天一次备份检测（每四天凌晨 4:00）
   0 4 */4 * * /bin/bash /path/to/backend/scripts/check_backup.sh >> /path/to/backend/logs/backup_check.log 2>&1
   ```

   **注意**：请将 `/path/to/backend` 替换为实际的项目路径。

3. **重启 crontab 服务**:
   ```bash
   sudo service cron restart
   ```

### Windows 系统 (使用任务计划程序)

1. **打开任务计划程序**:
   - 按下 `Win + R`，输入 `taskschd.msc`，然后按 Enter。

2. **创建每周小型备份任务**:
   - 点击 "创建任务"。
   - 在 "常规" 选项卡中，输入任务名称，例如 "MongoDB 每周小型备份"。
   - 在 "触发器" 选项卡中，点击 "新建"，设置每周日凌晨 2:00 运行。
   - 在 "操作" 选项卡中，点击 "新建"，设置程序为 `cmd.exe`，参数为 `/c "E:\GraduationProject\Backend\scripts\backup_mongodb.bat incremental"`。
   - 在 "条件" 和 "设置" 选项卡中，根据需要进行配置。
   - 点击 "确定" 保存任务。

3. **创建每月完整备份任务**:
   - 类似步骤 2，设置每月 1 日凌晨 3:00 运行，参数为 `/c "E:\GraduationProject\Backend\scripts\backup_mongodb.bat full"`。

4. **创建每四天备份检测任务**:
   - 类似步骤 2，设置每四天凌晨 4:00 运行，参数为 `/c "E:\GraduationProject\Backend\scripts\check_backup.bat"`。

## 2. 备份存储

### 本地存储
- 备份文件默认存储在 `./backups` 目录中。
- 备份脚本会自动清理 7 天前的备份文件，避免存储空间被占满。

### 远程存储（推荐）
- **云存储**：将备份文件上传到云存储服务（如 AWS S3、阿里云 OSS 等）。
- **网络存储**：将备份文件复制到网络存储设备（如 NAS）。
- **异地存储**：将备份文件复制到不同地理位置的存储设备。

## 3. 数据恢复流程

### 1. 准备工作
- 确保 MongoDB 服务已停止。
- 确保有足够的存储空间来恢复数据。

### 2. 恢复数据

#### 从完整备份恢复
```bash
# 解压备份文件
tar -xzf ./backups/mongodb_full_20260412_123456.tar.gz

# 恢复数据
mongorestore --host localhost:27017 --db graduation_project ./mongodb_backup/graduation_project
```

#### 从增量备份恢复
```bash
# 先恢复最近的完整备份
tar -xzf ./backups/mongodb_full_20260401_123456.tar.gz
mongorestore --host localhost:27017 --db graduation_project ./mongodb_backup/graduation_project

# 然后恢复增量备份
tar -xzf ./backups/mongodb_incremental_20260408_123456.tar.gz
mongorestore --host localhost:27017 --db graduation_project ./mongodb_backup/graduation_project
```

### 3. 验证恢复
- 启动 MongoDB 服务。
- 连接到 MongoDB，检查数据是否完整。
- 运行应用程序，确保一切正常。

## 4. 备份检测

备份检测脚本会自动运行，检查以下内容：
- 备份目录是否存在
- 是否有备份文件
- 备份文件是否完整
- 备份文件的大小和时间

检测结果会输出到 `./logs/backup_check.log` 文件中。

## 5. 常见问题

### 1. 备份失败
- 检查 MongoDB 服务是否正常运行。
- 检查备份目录权限是否正确。
- 检查磁盘空间是否足够。

### 2. 恢复失败
- 检查备份文件是否完整。
- 检查 MongoDB 服务是否已停止。
- 检查磁盘空间是否足够。

### 3. 定时任务不运行
- 检查 crontab 服务是否正常运行（Linux）。
- 检查任务计划程序是否正确配置（Windows）。
- 检查脚本权限是否正确。

## 6. 最佳实践

- **定期测试备份**：每月至少测试一次备份恢复过程。
- **多重备份**：同时使用本地备份和远程备份。
- **加密备份**：对敏感数据的备份进行加密。
- **版本控制**：保留多个版本的备份，以便回滚到不同的时间点。
- **监控备份**：设置备份失败告警机制。
