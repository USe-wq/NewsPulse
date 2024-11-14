import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.progress import Progress
from rich.console import Console
from rich.table import Table
from datetime import datetime
from urllib.parse import urlparse
import re
from base_crawler import *

class FREEtime(BaseCrawler):
    def __init__(self, base_url: str, options: Options = Options(), article_limit: int = 100):
        super().__init__(base_url, options, article_limit)

    def fetch_news(self) -> NewsList:
        news_list: NewsList = []  # Initialize a list, using NewsList only as a type hint
        
# 設置 Chrome 驅動程式的路徑
chromeDriverPath = r"C:\path\to\chromedriver-win64\chromedriver.exe"  # 請修改成你的 chromedriver 路徑

# 用來儲存爬取的新聞數據
news_list = []  # 使用 news_list 來儲存資料

# 用來追蹤已抓取的新聞網址
seen_urls = set()

# 設定目標日期為當天日期
target_date = datetime.now().strftime("%Y/%m/%d")  # 轉換為 "YYYY/MM/DD" 格式

# 用於顯示進度的 Console 實例
console = Console()

# 偵測不希望處理的網址並自動關閉
def close_unwanted_tabs(browser):
    current_url = browser.current_url
    unwanted_urls = ["talk.ltn", "estate.ltn", "auto.ltn", "istyle.ltn"]
    if any(url in current_url for url in unwanted_urls):
        browser.close()  # 關閉當前分頁
        browser.switch_to.window(browser.window_handles[0])  # 切換回主分頁
        return True  # 表示已關閉分頁
    return False

# 每個執行緒負責抓取一個頁面的新聞
def scrape_news_page(start_page, end_page, progress_bar):
    global news_list, seen_urls

    # 設置 Chrome 的選項
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-notifications")
    # chrome_options.add_argument('--headless')  # 刪除或註解掉這行來禁用無頭模式，讓瀏覽器顯示出來

    # 使用 Service 類別來初始化驅動程式
    service = Service(chromeDriverPath)
    browser = webdriver.Chrome(service=service, options=chrome_options)

    # 開啟新聞網站
    url = "https://ec.ltn.com.tw/list/strategy"
    browser.get(url)
    time.sleep(3)  # 等待頁面加載

    # 滾動函數，模擬人為滾動
    def scroll_to_bottom():
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, "//ul[@class='list boxTitle listpage_news']/li"))
        )  # 等待更多內容加載
        time.sleep(3)  # 增加等待時間以確保內容加載

    # 開始抓取新聞
    for page_num in range(start_page, end_page + 1):
        try:
            # 滾動到頁面底部以加載更多新聞
            scroll_to_bottom()

            articles = browser.find_elements(By.XPATH, "//ul[@class='list boxTitle listpage_news']/li")
            if not articles:
                break  # 如果沒有更多的文章，退出循環

            for article in articles:
                try:
                    # 抓取新聞時間
                    time_element = article.find_element(By.XPATH, ".//div[@class='tit']//font[@class='newstime']")
                    news_time = time_element.text if time_element else "未知時間"

                    # 使用正則表達式提取 "YYYY/MM/DD" 格式的日期（忽略時間部分）
                    match = re.match(r"(\d{4}/\d{2}/\d{2})", news_time)
                    if match:
                        formatted_date = match.group(1)  # 這裡會只抓取 "YYYY/MM/DD" 部分

                        if formatted_date != target_date:
                            continue  # 如果日期不匹配，跳過這條新聞

                    # 先抓取外部頁面的標題
                    title = article.find_element(By.XPATH, ".//a").text  # 查找 a 標籤中的文本
                    link = article.find_element(By.XPATH, ".//a").get_attribute('href')  # 獲取超鏈接地址

                    # 打印出來檢查是否成功抓取標題和鏈接
                    print(f"Title (before clicking): {title}, Link: {link}, Time: {news_time}")

                    # 檢查是否已經抓取過這條新聞
                    if link in seen_urls:
                        continue  # 如果新聞網址已經存在，跳過這條新聞
                    seen_urls.add(link)  # 記錄這條新聞的網址，避免重複抓取

                    # 點擊進入新聞詳情頁面抓取內容
                    browser.execute_script("window.open(arguments[0]);", link)  # 開啟新分頁
                    browser.switch_to.window(browser.window_handles[-1])  # 切換到新分頁
                    time.sleep(3)  # 等待頁面加載

                    # 等待內容加載，確保所有 <p> 標籤加載完成
                    WebDriverWait(browser, 100).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='whitecon boxTitle boxText']//p")))

                    # 抓取所有 <p> 標籤的內容，逐段抓取
                    content = ""
                    paragraphs = browser.find_elements(By.XPATH, "//div[@class='whitecon boxTitle boxText']//p")

                    # 遍歷每個段落並將其內容加入到 content
                    for paragraph in paragraphs:
                        content += paragraph.text + "\n"  # 每段文字後加上換行符
                        print(paragraph.text)  # 打印每段內容以便檢查

                    # 顯示抓取的所有內容
                    print(content)

                    # 儲存資料
                    news_list.append({
                        "id": len(news_list) + 1,
                        "time": news_time, 
                        "title": title,
                        "content": content,
                        "url": link,
                        "domain": urlparse(link).netloc
                    })

                    # 顯示儲存的資料
                    print(news_list)

                    browser.close()  # 關閉當前新聞分頁
                    browser.switch_to.window(browser.window_handles[0])  # 切換回主分頁

                    # 更新進度條
                    progress_bar.update(1)

                except Exception as e:
                    print(f"Error processing article: {e}")
                    browser.switch_to.window(browser.window_handles[0])  # 確保在發生錯誤時返回主分頁
                    continue

        except Exception as e:
            print(f"Error during page scraping: {e}")
            break

    # 關閉瀏覽器
    browser.quit()

# 使用 threading 來開啟兩個執行緒進行爬取
def start_scraping():
    # 記錄開始時間
    start_time = time.time()

    # 創建進度條
    with Progress() as progress:
        task = progress.add_task("[red]爬取中...", total=20)  # 假設有 20 頁新聞需要爬取

        # 創建表格來顯示統計數據
        table = Table(title="爬取統計")
        table.add_column("項目", justify="right", style="cyan", no_wrap=True)
        table.add_column("數值", style="magenta")

        # 開啟兩個執行緒
        threads = []
        for i in range(2):
            start_page = i * 10 + 1
            end_page = (i + 1) * 10
            thread = threading.Thread(target=scrape_news_page, args=(start_page, end_page, progress))
            threads.append(thread)
            thread.start()

        # 等待所有執行緒完成
        for thread in threads:
            thread.join()

        # 統計數據
        total_time = time.time() - start_time
        table.add_row("總爬取時間", f"{total_time:.2f} 秒")
        table.add_row("總共抓取新聞數量", f"{len(news_list)} 條")
        console.print(table)

# 開始爬取
start_scraping()
