#!/bin/bash
# 快速推送 5.0 版本到 Gitee 的脚本
# 使用方法: bash QUICK_PUSH.sh

echo "=== 开始推送 5.0 版本 ==="

# 0. 配置 git 用户信息（如果需要）
echo "0. 配置 git 用户信息..."
git config --global user.name 'JiangHan1913'
git config --global user.email 'jh18954242606@163.com'

# 0.1. 确保 Gitee 远程仓库已配置
echo "0.1. 配置 Gitee 远程仓库..."
git remote add gitee https://gitee.com/jianghan1913/Humanoid-robot-21Dof-stair-amp.git 2>/dev/null || \
git remote set-url gitee https://gitee.com/jianghan1913/Humanoid-robot-21Dof-stair-amp.git 2>/dev/null || \
git remote set-url origin https://gitee.com/jianghan1913/Humanoid-robot-21Dof-stair-amp.git

# 1. 添加所有更改
echo "1. 添加所有更改..."
git add .

# 2. 提交更改
echo "2. 提交更改..."
git commit -m "feat: 发布 5.0 版本

- 添加对称损失（Symmetry Loss）适配RNN网络
  - 使用独立的镜像网络副本处理镜像数据
  - 在计算前保存镜像hidden states，确保训练时状态正确性
  - 完全支持LSTM/GRU等循环神经网络结构
- AMP训练时加入手脚位置对比，提升模仿精度
- 增加足底力平滑奖励，提升运动稳定性
- AMP风格奖励调整为固定值，提升训练稳定性
- 实现稳定的上下楼梯和精准的落足点规划
- 更新 README 文档和版本记录"

# 3. 创建 v5.0 分支（如果不存在）
echo "3. 创建/切换到 v5.0 分支..."
git checkout -b v5.0 2>/dev/null || git checkout v5.0

# 4. 推送到 Gitee（明确指定分支，强制推送）
echo "4. 推送到 Gitee..."
REMOTE=$(git remote | grep -E '^(gitee|origin)$' | head -1)
if [ -z "$REMOTE" ]; then
    REMOTE="origin"
fi
# 明确指定推送分支，强制推送，避免与标签冲突，显示进度
echo "   正在强制推送分支 v5.0..."
git push --progress --force-with-lease -u $REMOTE refs/heads/v5.0:refs/heads/v5.0

# 5. 创建并推送标签
echo "5. 创建版本标签..."
# 如果标签已存在，先删除本地标签
git tag -d v5.0 2>/dev/null
git tag -a v5.0 -m "版本 5.0: 对称损失适配RNN、AMP手脚位置对比、足底力平滑奖励、固定风格奖励、楼梯运动优化"
# 明确指定推送标签，强制推送，避免与分支冲突，显示进度
echo "   正在强制推送标签 v5.0..."
git push --progress --force $REMOTE refs/tags/v5.0:refs/tags/v5.0

echo ""
echo "=== 推送完成！ ==="
echo "查看仓库: https://gitee.com/jianghan1913/Humanoid-robot-21Dof-stair-amp"
echo "分支: v5.0"
echo "标签: v5.0"

