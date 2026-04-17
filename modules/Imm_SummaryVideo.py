#可以正常爬取视频链接以及标题并且发送邮箱
#想办法提取视频内容（未完成） ==>>   https://tpv.vlogdownloader.com/   ==>> 新的url发送给通问悟听
#或者直接下载，然后发送给通问悟听
#目前并不清楚，如何让程序自动执行以上功能
#最后一个功能便是将总结的内容记录至谣言库

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import smtplib
import json
import time
import schedule
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# 加载环境变量
load_dotenv()

# ===================== 配置项（请修改为自己的信息） =====================
# 需监控的UP主UID列表（可添加多个）
UP_UID_LIST = ["99443903", "67389029"]
# 检查更新间隔（单位：分钟，建议5-10分钟）
CHECK_INTERVAL = 5
# 已监控视频ID存储文件（持久化，避免重启后重复推送）
HISTORY_FILE = "video_history.json"
# 邮箱配置
SMTP_SERVER = "smtp.qq.com"  # QQ邮箱：smtp.qq.com；163邮箱：smtp.163.com
SMTP_PORT = 465
SEND_EMAIL = os.getenv("SEND_EMAIL")  # 发件人邮箱（.env文件中配置）
SEND_PASSWORD = os.getenv("SEND_PASSWORD")  # 邮箱SMTP授权码
RECEIVE_EMAIL = os.getenv("RECEIVE_EMAIL")  # 收件人邮箱


# ==========================================================================

# 初始化历史记录（字典：{uid: {video_bv: 1}}）
def init_history():
    """初始化/加载已监控视频历史记录"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # 首次运行，初始化空字典
        history = {uid: {} for uid in UP_UID_LIST}
        save_history(history)
        return history


def save_history(history):
    """保存历史记录到JSON文件"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_video_detail(bv_id):
    """从视频详情页提取标题、简介（解决标题/简介缺失问题）"""
    url = f"https://www.bilibili.com/video/{bv_id}/"
    print(f"正在获取视频详情：{url}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # 访问详情页，等待动态加载
            page.goto(url, wait_until="networkidle")
            time.sleep(2)

            # 提取标题（h1标签）
            title = page.locator("h1.video-title").inner_text().strip()
            # 提取简介（.video-desc 标签）
            desc_locator = page.locator(".video-desc")
            desc = desc_locator.inner_text().strip() if desc_locator.count() > 0 else "无简介"

            browser.close()
            return {
                "title": title,
                "desc": desc,
                "url": url
            }
        except Exception as e:
            print(f"获取视频详情失败：{e}")
            return {"title": "未知标题", "desc": "获取简介失败", "url": url}


def get_up_latest_videos(uid):
    """获取指定UP主的所有公开视频（BV号列表）"""
    url = f"https://space.bilibili.com/{uid}/video"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # 访问UP主视频页
            page.goto(url, wait_until="networkidle")
            time.sleep(2)

            # 修复：使用 all() 方法获取所有元素，然后逐个提取 href
            video_elements = page.locator("a.bili-cover-card").all()
            bv_list = []
            for element in video_elements:
                link = element.get_attribute("href")
                if link and "BV" in link:
                    bv = link.split("BV")[1].split("/")[0]
                    bv = f"BV{bv}"  # 拼接完整BV号
                    bv_list.append(bv)

            browser.close()
            # 去重并保持顺序（最新的在前）
            bv_list = list(dict.fromkeys(bv_list))
            return bv_list
        except Exception as e:
            print(f"获取UP主{uid}视频列表失败：{e}")
            return []


def send_email_notification(uid, video_detail):
    """发送视频更新邮件（含UID、标题、简介、链接）"""
    if not video_detail:
        print("无视频详情，跳过邮件发送")
        return False

    # 先处理简介中的换行符，避免在 f-string 里用反斜杠
    desc_html = video_detail['desc'].replace('\n', '<br>')

    # 邮件内容（格式化显示所有信息）
    content = f"""
<div style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6;">
  <h2 style="color: #2d8cf0;">B站UP主视频更新提醒</h2>
  <hr>
  <p><strong>UP主UID：</strong>{uid}</p>
  <p><strong>视频标题：</strong>{video_detail['title']}</p>
  <p><strong>视频简介：</strong><br>{desc_html}</p>
  <p><strong>视频链接：</strong><a href="{video_detail['url']}" target="_blank">{video_detail['url']}</a></p>
  <p><strong>推送时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <hr>
  <p style="color: #999; font-size: 12px;">--- 自动监控推送，无需回复 ---</p>
</div>
    """

    try:
        msg = MIMEText(content, "html", "utf-8")
        msg["From"] = SEND_EMAIL
        msg["To"] = RECEIVE_EMAIL
        msg["Subject"] = Header(f"【B站更新】UID-{uid}：{video_detail['title'][:20]}...", "utf-8")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SEND_EMAIL, SEND_PASSWORD)
            server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())

        print(f"✅ 邮件推送成功（UID-{uid}）：{video_detail['title']}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮件登录失败：检查邮箱/授权码是否正确（授权码不是登录密码）")
        return False
    except Exception as e:
        print(f"❌ 邮件发送失败（UID-{uid}）：{e}")
        return False


def check_new_videos(is_first_run=False):
    """检查所有UP主的新视频（首次运行发送最新视频测试）"""
    print(f"\n===== 开始检查更新（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）=====")
    history = init_history()

    for uid in UP_UID_LIST:
        print(f"\n🔍 检查UP主 UID-{uid}...")
        # 获取该UP主所有视频BV号
        bv_list = get_up_latest_videos(uid)
        if not bv_list:
            print(f"UID-{uid} 无公开视频")
            continue

        # 筛选未监控的新视频（最新的在前）
        new_bv_list = [bv for bv in bv_list if bv not in history[uid]]

        if is_first_run:
            # 首次运行：发送最新1个视频测试
            latest_bv = bv_list[0]
            print(f"首次运行，发送UID-{uid}最新视频测试：{latest_bv}")
            video_detail = get_video_detail(latest_bv)
            send_email_notification(uid, video_detail)
            # 将该视频加入历史记录
            history[uid][latest_bv] = 1
            save_history(history)
        elif new_bv_list:
            # 非首次运行：仅发送新增视频
            print(f"UID-{uid} 检测到 {len(new_bv_list)} 个新视频")
            for bv in new_bv_list:
                video_detail = get_video_detail(bv)
                send_email_notification(uid, video_detail)
                # 加入历史记录
                history[uid][bv] = 1
            save_history(history)
        else:
            print(f"UID-{uid} 暂无新视频")


if __name__ == "__main__":
    # 初始化历史记录
    init_history()
    print(f"📌 程序启动，监控 {len(UP_UID_LIST)} 个UP主，检查间隔 {CHECK_INTERVAL} 分钟")

    # 首次运行：发送所有UP主最新视频测试
    print("\n===== 首次运行，发送最新视频测试 =====")
    check_new_videos(is_first_run=True)

    # 定时任务：每隔指定分钟检查一次
    schedule.every(CHECK_INTERVAL).minutes.do(check_new_videos, is_first_run=False)

    print(f"\n===== 定时监控已启动（按 Ctrl+C 停止）=====")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✅ 程序已手动停止")