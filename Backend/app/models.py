from transformers import pipeline
import json
import sys
from collections import Counter
import warnings
warnings.filterwarnings("ignore")

# ============================
# 模型加载（英文 + 俄语）
# ============================
english_model = pipeline(
    "text-classification",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    truncation=True,  # 关键：自动截断超长文本
    max_length=512    # 模型最大长度限制
)

russian_model = pipeline(
    "text-classification",
    model="seara/rubert-tiny2-russian-sentiment",
    truncation=True,
    max_length=512
)

# ============================
# 偏好 & 避讳词典
# ============================
PREFERENCE_EN = [
    "quality", "durable", "material", "soft", "beautiful",
    "fast delivery", "packaging", "price", "size", "fit",
    "color", "design", "comfortable", "easy to use"
]
TABOO_EN = [
    "too small", "too big", "uncomfortable", "fragile",
    "broken", "bad quality", "ugly", "wrong color", "offensive"
]

PREFERENCE_RU = [
    "качество", "прочный", "материал", "мягкий", "удобный",
    "быстрая доставка", "упаковка", "цена", "размер", "цвет"
]
TABOO_RU = [
    "слишком маленький", "слишком большой", "неудобный",
    "хрупкий", "сломан", "плохое качество", "некрасивый"
]

# ============================
# 分析单条评论（新增超长文本处理）
# ============================
def analyze_review(text, lang="en"):
    text = str(text).strip()
    # 手动截断超长文本（双重保险）
    if len(text) > 500:
        text = text[:500]
    
    if lang == "en":
        sent = english_model(text)[0]
        pref = [w for w in PREFERENCE_EN if w in text.lower()]
        taboo = [w for w in TABOO_EN if w in text.lower()]
    else:
        sent = russian_model(text)[0]
        pref = [w for w in PREFERENCE_RU if w in text.lower()]
        taboo = [w for w in TABOO_RU if w in text.lower()]

    return {
        "review": text,
        "sentiment": sent["label"],
        "confidence": round(sent["score"], 4),
        "preferences": pref,
        "taboos": taboo
    }

# ============================
# 读取 TXT 文件
# ============================
def read_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        # 兼容GBK编码的TXT文件
        with open(file_path, "r", encoding="gbk") as f:
            return [line.strip() for line in f if line.strip()]

# ============================
# 批量分析 + 输出报告
# ============================
def run_analysis(file_path, lang="en"):
    print(f"正在分析文件：{file_path}")
    reviews = read_txt(file_path)
    if not reviews:
        print("❌ 未读取到评论，请检查文件是否为空或编码错误")
        return
    
    results = []
    all_prefs = []
    all_taboos = []

    for idx, r in enumerate(reviews):
        try:
            res = analyze_review(r, lang)
            results.append(res)
            all_prefs.extend(res["preferences"])
            all_taboos.extend(res["taboos"])
        except Exception as e:
            print(f"⚠️ 第{idx+1}条评论分析失败：{e}")
            continue

    report = {
        "total": len(results),
        "success": len(results),
        "failed": len(reviews) - len(results),
        "top_preferences": Counter(all_prefs).most_common(10),
        "top_taboos": Counter(all_taboos).most_common(10),
        "details": results
    }

    # 输出报告
    out_file = "报告_" + file_path.replace(".txt", ".json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("✅ 分析完成！")
    print(f"📊 总评论数：{len(reviews)}")
    print(f"✅ 成功分析：{len(results)}")
    print(f"❌ 分析失败：{len(reviews)-len(results)}")
    print(f"👍 高频偏好：{report['top_preferences']}")
    print(f"🚫 高频避讳：{report['top_taboos']}")
    print(f"📄 完整报告：{out_file}")

# ============================
# PowerShell 命令入口
# ============================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法：python analyze_final.py 文件名.txt [en/ru]")
        print("示例：python analyze_final.py test.txt en")
    else:
        file = sys.argv[1]
        lang = sys.argv[2] if len(sys.argv) > 2 else "en"
        run_analysis(file, lang)