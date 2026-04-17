import json
import os
import re
import csv
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

import config

# ====================== 可配置参数 ======================
UID = "1391465764"
SAVE_DIR = config.BASE_DIR / "data"
JSON_PATH = os.path.join(SAVE_DIR, "bili_rumor.json")
CSV_PATH = os.path.join(SAVE_DIR, "train_rumor.csv")

# 新增自定义参数
ARTICLE_START = 1  # 起始文章索引（从1开始）
ARTICLE_END = -1  # 结束文章索引
MAX_ARTICLES = -1  # 最大获取专栏数（-1表示全部）
LOG_DIR = config.LOG_DIR  # 日志目录
# ==================================================

# 初始化日志配置
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"bili_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ===================================
# 1. 滚动加载文章（支持最大数量限制 + 适配两种链接格式）
# ===================================
def get_all_articles(uid, max_articles=-1):
    articles = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
            )

            url = f"https://space.bilibili.com/{uid}/article"
            try:
                page.goto(url, timeout=60000)
                page.wait_for_selector("a[href*='/opus/'], a[href*='/read/cv']", timeout=15000)
            except Exception as e:
                logger.error(f"❌ [CRITICAL] 加载专栏页面失败 | URL: {url} | 错误: {str(e)}")
                browser.close()
                return []

            last_count = 0
            repeat = 0
            while repeat < 12:
                # 达到最大数量则停止加载
                if max_articles != -1 and last_count >= max_articles:
                    break
                try:
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(1200)
                    # 同时匹配两种链接格式
                    current = page.query_selector_all("a[href*='/opus/'], a[href*='/read/cv']")
                    current_count = len(current)
                    if current_count == last_count:
                        repeat += 1
                    else:
                        repeat = 0
                        last_count = current_count
                        print(f"已加载：{last_count} 篇")
                except Exception as e:
                    logger.error(f"❌ [CRITICAL] 滚动加载失败 | 错误: {str(e)}")
                    repeat += 1

            # 限制最大获取数量
            items = page.query_selector_all("a[href*='/opus/'], a[href*='/read/cv']")
            if max_articles != -1 and len(items) > max_articles:
                items = items[:max_articles]

            # 解析两种链接格式
            for a in items:
                try:
                    href = a.get_attribute("href")
                    title = a.inner_text().strip()
                    # 匹配 /opus/xxx 格式
                    opus_match = re.search(r"/opus/(\d+)", href)
                    # 匹配 /read/cvxxx 格式
                    cv_match = re.search(r"/read/cv(\d+)", href)

                    if opus_match:
                        article_id = opus_match.group(1)
                        article_type = "opus"
                    elif cv_match:
                        article_id = cv_match.group(1)
                        article_type = "cv"
                    else:
                        continue  # 不识别的链接格式跳过

                    articles.append({
                        "article_id": article_id,
                        "article_type": article_type,
                        "title": title,
                        "href": href
                    })
                except Exception as e:
                    logger.error(f"❌ [CRITICAL] 解析文章失败 | 错误: {str(e)}")
                    continue

            browser.close()
            print(f"\n✅ 文章列表加载完成：{len(articles)} 篇")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] 获取文章列表整体失败: {str(e)}")
    return articles


# ===================================
# 2. 单篇文章（适配两种链接格式 + 超级稳定）
# ===================================
def get_content_safe(article_id, article_type):
    content = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
            page = browser.new_page()
            # 根据类型拼接不同的URL
            if article_type == "opus":
                url = f"https://www.bilibili.com/opus/{article_id}"
            else:  # cv类型
                url = f"https://www.bilibili.com/read/cv{article_id}"

            page.goto(url, timeout=12000)
            page.wait_for_timeout(2000)

            # 兼容两种页面的内容选择器
            selectors = [
                ".opus-module-content p",  # opus类型内容
                ".article-holder p",  # cv类型内容
                "#article-content p"  # 备用cv内容选择器
            ]

            for selector in selectors:
                p_list = page.query_selector_all(selector)
                if p_list:
                    content = "\n".join([p.inner_text().strip() for p in p_list if p.inner_text().strip()])
                    break

            browser.close()
    except Exception as e:
        logger.error(f"❌ [CRITICAL] 获取文章内容失败 [id={article_id}, type={article_type}]: {str(e)}")

    return content if len(content) > 20 else ""


# ===================================
# 3. 拆分谣言
# ===================================
def split_rumors(text):
    rumors = []
    try:
        current = ""
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("详情：") or line.startswith("真相："):
                if current:
                    rumors.append(current.strip())
                current = line
            else:
                current += " " + line
        if current:
            rumors.append(current.strip())
    except Exception as e:
        logger.error(f"❌ [CRITICAL] 拆分谣言内容失败: {str(e)}")
    return rumors


# ===================================
# 4. 导出训练CSV
# ===================================
def save_to_csv(data, csv_path):
    try:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["text", "label"])
            for item in data:
                for r in item.get("rumors", []):
                    if r:
                        writer.writerow([r, 1])
        logger.info(f"CSV文件保存成功: {csv_path}")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] 保存CSV文件失败: {str(e)}")


# ===================================
# 主函数（支持范围筛选 + 绝对不崩溃）
# ===================================
def main():
    # 1. 获取文章列表（支持最大数量限制）
    articles = get_all_articles(UID, MAX_ARTICLES)
    if not articles:
        print("❌ 未获取到文章列表")
        logger.warning("未获取到任何文章列表")
        return

    # 2. 截取指定范围的文章（100-150）
    # 索引转换：列表从0开始，参数从1开始
    start_idx = ARTICLE_START - 1
    end_idx = ARTICLE_END
    target_articles = articles[start_idx:end_idx] if len(articles) > start_idx else []

    if not target_articles:
        print(f"❌ 无符合范围的文章（{ARTICLE_START}-{ARTICLE_END}）")
        logger.warning(f"无符合范围的文章（{ARTICLE_START}-{ARTICLE_END}），总文章数：{len(articles)}")
        return

    print(f"\n🎯 筛选出 {ARTICLE_START}-{ARTICLE_END} 范围的文章：{len(target_articles)} 篇")

    # 3. 解析目标文章内容
    result = []
    total = len(target_articles)

    for idx, art in enumerate(target_articles, 1):
        article_id = art["article_id"]
        article_type = art["article_type"]
        title = art["title"]
        print(f"[{idx}/{total}] {title} (type: {article_type})")

        content = get_content_safe(article_id, article_type)
        if not content:
            print("   ⏭️  无内容/超时/删除 → 跳过")
            continue

        rumors = split_rumors(content)
        result.append({
            "id": article_id,
            "type": article_type,
            "title": title,
            "rumors": rumors
        })

    # 4. 保存结果
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON文件保存成功: {JSON_PATH}")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] 保存JSON文件失败: {str(e)}")

    save_to_csv(result, CSV_PATH)

    print(f"\n🎉 全部完成！")
    print(f"📄 有效文章：{len(result)} 篇")
    print(f"📄 JSON路径：{JSON_PATH}")
    print(f"📄 CSV路径：{CSV_PATH}")
    print(f"📄 日志路径：{log_filename}")


if __name__ == "__main__":
    main()