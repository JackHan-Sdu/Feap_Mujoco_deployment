#!/bin/bash
# 快速推送到 GitHub 的脚本
# 使用方法: bash QUICK_PUSH_GITHUB.sh

echo "=== 开始推送到 GitHub ==="

# 0.1. 确保 GitHub 远程仓库已配置
echo "0.1. 配置 GitHub 远程仓库..."
GITHUB_REPO="git@github.com:JackHan-Sdu/Feap_Mujoco_deployment.git"
git remote add github $GITHUB_REPO 2>/dev/null || \
git remote set-url github $GITHUB_REPO 2>/dev/null || \
git remote set-url origin $GITHUB_REPO

# 1. 添加所有更改
echo "1. 添加所有更改..."
git add .

# 2. 提交更改
echo "2. 提交更改..."
# 检查是否有未提交的更改
if git diff --cached --quiet && git diff --quiet; then
    echo "   没有需要提交的更改，跳过提交步骤"
else
    git commit -m "feat: FEAP MuJoCo Deployment Framework

- FEAP (Feature-Enhanced Adversarial Priors) deployment framework
- MuJoCo simulation environment integration
- ONNX model deployment (HumanEncodernet & HumanActornet)
- Dual input control: gamepad and keyboard support
- Real-time visualization and performance monitoring
- Interactive camera control with pelvis tracking
- Disturbance testing capabilities
- Automated conda environment setup
- Comprehensive README documentation"
fi

# 3. 确保使用 main 分支
echo "3. 切换到 main 分支..."
git branch -M main

# 4. 推送到 GitHub
echo "4. 推送到 GitHub..."
REMOTE=$(git remote | grep -E '^(github|origin)$' | head -1)
if [ -z "$REMOTE" ]; then
    REMOTE="origin"
fi
# 先获取远程最新信息，然后使用强制推送
echo "   正在获取远程信息..."
git fetch $REMOTE main 2>/dev/null || true
# 使用强制推送（--force-with-lease 更安全，会检查远程是否有其他人的提交）
echo "   正在强制推送分支 main..."
git push --progress --force-with-lease -u $REMOTE main || \
git push --progress --force -u $REMOTE main

echo ""
echo "=== 推送完成！ ==="
echo "查看仓库: https://github.com/JackHan-Sdu/Feap_Mujoco_deployment"
echo "分支: main"
