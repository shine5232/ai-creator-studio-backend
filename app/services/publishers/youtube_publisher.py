"""YouTube video publisher — Selenium headless Chrome upload."""

import os
import re
import time

from app.services.publishers.base import BasePublisher, PublishContext, PublishResult
from app.utils.logger import logger


class YouTubePublisher(BasePublisher):
    platform_name = "youtube"

    # ── cookie validation ────────────────────────────────────────────────────

    async def validate_cookies(self, cookies: dict) -> bool:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

            driver = webdriver.Chrome(options=options)
            try:
                driver.get("https://www.youtube.com")
                for name, value in cookies.items():
                    driver.add_cookie({"name": name, "value": str(value), "domain": ".youtube.com"})
                driver.get("https://www.youtube.com")
                time.sleep(3)
                # Check if logged in by looking for avatar / account button
                page_source = driver.page_source
                return "accounts.google.com" not in driver.current_url and (
                    '"isCollapsed":false' in page_source
                    or 'avatar' in page_source.lower()
                    or 'Sign in' not in driver.title
                )
            finally:
                driver.quit()
        except Exception as exc:
            logger.warning(f"YouTube cookie validation failed: {exc}")
            return False

    # ── status check ─────────────────────────────────────────────────────────

    async def check_status(self, platform_post_id: str, cookies: dict) -> dict:
        video_url = f"https://www.youtube.com/watch?v={platform_post_id}"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(video_url)
                if resp.status_code == 200 and platform_post_id in resp.text:
                    return {"video_id": platform_post_id, "status": "published"}
                return {"video_id": platform_post_id, "status": "unknown"}
        except Exception as exc:
            return {"video_id": platform_post_id, "error": str(exc)}

    # ── upload ───────────────────────────────────────────────────────────────

    async def upload_video(self, ctx: PublishContext) -> PublishResult:
        if not os.path.isfile(ctx.video_path):
            return PublishResult(success=False, error=f"Video file not found: {ctx.video_path}")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=en-US")
            options.add_argument("--window-size=1920,1080")

            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 30)

            try:
                # Step 1: inject cookies
                driver.get("https://www.youtube.com")
                time.sleep(2)
                for name, value in ctx.cookies.items():
                    driver.add_cookie({
                        "name": name,
                        "value": str(value),
                        "domain": ".youtube.com",
                    })

                # Step 2: navigate to YouTube Studio
                driver.get("https://studio.youtube.com")
                time.sleep(5)

                # Verify we're in studio
                if "accounts.google.com" in driver.current_url:
                    return PublishResult(success=False, error="cookie_expired")

                # Step 3: click upload button
                upload_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "ytcp-button#create-icon")
                ))
                upload_btn.click()
                time.sleep(1)

                upload_option = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//ytcp-ve[contains(text(),'Upload videos')]")
                ))
                upload_option.click()
                time.sleep(1)

                # Step 4: select file
                file_input = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='file']")
                ))
                file_input.send_keys(os.path.abspath(ctx.video_path))

                # Step 5: wait for upload to complete — poll progress
                logger.info("YouTube: video uploading, waiting for completion...")
                max_wait = 1200  # 20 minutes
                start = time.time()
                while time.time() - start < max_wait:
                    try:
                        # Look for "Checks" tab which appears after upload + processing
                        checks = driver.find_elements(
                            By.XPATH, "//div[contains(text(),'Checks')]"
                        )
                        if checks:
                            break
                    except Exception:
                        pass
                    time.sleep(10)

                # Step 6: fill in details
                title_input = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div#title-textarea textarea, input#title")
                ))
                # Clear existing title
                title_input.clear()
                title_input.send_keys(ctx.title)

                if ctx.description:
                    try:
                        desc_box = driver.find_element(
                            By.CSS_SELECTOR, "div#description-textarea textarea, div#description"
                        )
                        desc_box.clear()
                        desc_box.send_keys(ctx.description)
                    except Exception:
                        logger.warning("YouTube: could not set description")

                if ctx.tags:
                    try:
                        # Click "Show more" to reveal tags
                        show_more = driver.find_elements(
                            By.XPATH, "//button[contains(text(),'Show more')]"
                        )
                        if show_more:
                            show_more[0].click()
                            time.sleep(1)
                        tags_input = driver.find_element(
                            By.CSS_SELECTOR, "input#tags-container input"
                        )
                        tags_input.send_keys(",".join(ctx.tags))
                    except Exception:
                        logger.warning("YouTube: could not set tags")

                # Step 7: click Next through dialogs (visibility, checks)
                for _ in range(3):
                    try:
                        next_btn = driver.find_element(
                            By.CSS_SELECTOR, "ytcp-button#next-button"
                        )
                        next_btn.click()
                        time.sleep(2)
                    except Exception:
                        break

                # Step 8: click Publish
                publish_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "ytcp-button#publish-button")
                ))
                publish_btn.click()
                time.sleep(3)

                # Step 9: extract video_id from the success dialog URL
                video_id = None
                page_source = driver.page_source
                match = re.search(r'/watch\?v=([a-zA-Z0-9_-]{11})', page_source)
                if match:
                    video_id = match.group(1)
                else:
                    # Try to find in current URL or dialog
                    match = re.search(r'v=([a-zA-Z0-9_-]{11})', driver.current_url)
                    if match:
                        video_id = match.group(1)

                if not video_id:
                    return PublishResult(
                        success=False,
                        error="Could not extract video_id after publish",
                    )

                return PublishResult(
                    success=True,
                    platform_post_id=video_id,
                    platform_url=f"https://youtube.com/watch?v={video_id}",
                )
            finally:
                driver.quit()

        except Exception as exc:
            logger.error(f"YouTube upload failed: {exc}")
            return PublishResult(success=False, error=str(exc))
