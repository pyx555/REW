# config.py

# ================= 配置说明 =================
# 1. 如果使用 DeepSeek 官方 API:
#    API_URL = "https://api.deepseek.com/chat/completions"
#    MODEL_NAME = "deepseek-chat" (或者 deepseek-reasoner)
#
# 2. 如果使用 SiliconFlow (硅基流动):
#    API_URL = "https://api.siliconflow.cn/v1/chat/completions"
#    MODEL_NAME = "deepseek-ai/DeepSeek-V3"
# ===========================================

# 在此处填入你的 API 密钥
API_KEY = "sk-zykmdntdpotgibftsezijrmqypaywoshfboazjwslaktamsb" 

# 这里根据你的 Key 应该是 SiliconFlow 的格式，所以保留你原来的设置
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
LLM_MODEL_NAME = "deepseek-ai/DeepSeek-V3.2"

# 最大迭代次数
MAX_ITERATIONS = 8