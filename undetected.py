import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import undetected_chromedriver as uc

logging.basicConfig(level=logging.INFO)

# Configuration
TARGET_URL = "https://copilot.microsoft.com/chats"  # Change to Copilot URL if needed
OUTPUT_FILE = "page_content.txt"

# Set up Chrome options for headless browsing

def generate_data(text):
    #chrome_options = Options()
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")

    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Initialize WebDriver
    service = Service()
    #driver = webdriver.Chrome(service=service, options=chrome_options)
    driver = uc.Chrome(service=service, options=chrome_options)

    # text = """The golden divine soul clearly hadn’t expected Chen Ping to unleash such a rogue. It froze for a moment before roaring in anger, “How dare you! I am the ancestor of the Barbarian Clan, how dare a demon like you defile me!” “Ancestor?” Red Cloud Demon Lord scoffed, circling the divine soul before suddenly pointing at a crack in its battle armour and laughing loudly, “I thought you were some big shot, but turns out you got your armour cracked by a kick from that demon clan sow next door?” “Tch, how embarrassing. If word got out, where would your ancient clan’s face be?” The divine soul trembled with rage, its golden light surging, the totem shadows around it quivering, “You… how do you know?!” “I know a lot!” Red Cloud Demon Lord’s eyes widened as he leaned closer, a thick wave of demonic qi washing over the divine soul, “With your pathetic state, you call yourself an ancestor? Believe it or not, I could piss you to death with a single splash?” “Who the hell are you?” The Barbarian Clan ancestor stared at Red Cloud Demon Lord in growing fear. “I am Red Cloud Demon Lord…” Red Cloud Demon Lord declared his name slowly. “Red Cloud Demon Lord?” The Barbarian Clan ancestor’s eyes widened in shock. “What? You know me?” Red Cloud Demon Lord asked. “Of course! Thousands of years ago, you slaughtered tens of thousands of immortals in a single battle in the Ninth Heaven. Who doesn’t know you?” The Barbarian Clan ancestor flattered Red Cloud Demon Lord. Hearing this, Red Cloud Demon Lord scratched his head, a bit embarrassed, chuckling, “A hero doesn’t dwell on past glories. I’m just a strand of divine soul now, my physical body long destroyed.” “Since you know me, give me some face. Let my little brother take all your treasures. Your Barbarian Clan is already wiped out, so what use does a divine soul like you have for all this stuff?” Red Cloud Demon Lord’s words shattered the Barbarian Clan ancestor’s mental defences. He hadn’t expected his clan to already be eradicated. Looking at the unmasked mockery and threat in Red Cloud Demon Lord’s eyes, and then at Chen Ping’s faint, amused smile, the ancestor realised he was up against a tough opponent. He knew that if he didn’t agree, even this strand of divine soul wouldn’t survive. “Fine, the treasury is yours, but I hope you won’t touch my clan’s foundational heritage. When I reconstruct my body, I can still revive the Barbarian Clan!” With that, the Barbarian Clan ancestor turned into a streak of golden light, vanishing into a stone tablet deep in the treasury, silent thereafter. Chen Ping glanced at the departing ancestor, then at the smugly posing Red Cloud Demon Lord, and couldn’t help but smile. “Senior, your reputation is quite something!” Chen Ping flattered. “Of course! I was invincible below the Ninth Heaven!” Red Cloud Demon Lord laughed proudly. With a thought, Chen Ping recalled Red Cloud Demon Lord’s divine soul back into his sea of consciousness. “Oi, what’s wrong with letting me stay out a bit longer?” Red Cloud Demon Lord grumbled. “I’m worried your divine soul might get damaged if exposed too long. It’d be troublesome if you couldn’t reconstruct your body!” Chen Ping explained. At that, Red Cloud Demon Lord fell silent. Chen Ping waved his hand, and countless natural treasures, technique manuals, and ancient spiritual artefacts were instantly stored in his ring. What thrilled him most was a “Chaos Spiritual Root” embedded in a chaos stone, and a tattered scroll of the *Barbarian Body Refining Art*, exuding an ancient aura. The body-refining techniques recorded within were countless times superior to those of the ancient body-refining clans in the Celestial Realm. “With this refining art, my physical body will grow even stronger!” Chen Ping stored the *Barbarian Body Refining Art*, then turned his gaze to the Chaos Spiritual Root. The root was clearly still growing, and the immortal qi around it was noticeably denser."""
    
    full_prompt = (
        "You are a helpful assistant. Read the following story and extract all dialogue and narration into a JSON array. "
        "Each element in the array must follow this format: [actorName, Emotion, textSpoken, gender] "
        "Rules to follow strictly: 1. Use quotation marks to extract dialogue. 2. Include narration with \"actorName\" as \"narration\" and gender as null. "
        "3. Set Emotion based on cues like “mocked”, “roared”, “angrily”, etc., or null if none. 4. Derive gender from the name, use best judgment if unclear. "
        "5. Do not skip any part of the story — include every sentence. 6. Output only the JSON array — no explanations, no extra text. "
        "7. Wrap the entire JSON array inside a markdown code block (triple backticks), specifying json for syntax highlighting. "
        "Now process this story:\n\n"
        + text
    )
    

    # full_prompt = (
    #     "You are a voice synthesis expert. Read the following story and extract all dialogue and narration into a structured **JSON array** where each element follows this format:\n"
    #     "[actorName, Emotion, textSpoken, gender].\n"
    #     "Then, for each dialogue, **inject appropriate SSML tags** based on the **emotion** of the character and the context of the text. Use SSML tags like **prosody**, **emphasis**, **volume**, **rate**, **pitch**, **pause**, and other tags as appropriate to match the emotional tone of the dialogue.\n\n"
    #     "Additionally, include **breathing sounds** (`<amazon:auto-breaths/>`) at emotional or intense moments to make the speech sound more natural and human-like.\n"
    #     "- **Emotions** in the dialogue should be identified using context cues such as “mocked”, “roared”, “angrily”, “sadly”, etc.\n"
    #     "- The **SSML tags** should be applied **dynamically** based on the detected emotion and should not be limited to a pre-defined list.\n"
    #     "**Rules to follow strictly:**\n"
    #     "1. Use quotation marks to extract dialogue.\n"
    #     "2. Include narration with \"actorName\" as \"narration\" and gender as null.\n"
    #     "3. Set **Emotion** based on context and cues (e.g., \"mocked\", \"shouted\", \"sadly\", \"angrily\", etc.).\n"
    #     "4. Derive **gender** from the name, using best judgment if unclear.\n"
    #     "5. For **narrations**, use **<prosody>**  tags as needed to maintain pacing.\n"
    #     "6. Ensure the **SSML tags** are **relevant to the specific emotion** and tone.\n"
    #     "7. Output only the **JSON array** containing the SSML-enhanced dialogues and narrations.\n"
    #     "8. Wrap the entire JSON array inside a markdown code block (triple backticks), specifying `json` for syntax highlighting.\n"
    #     "9. **Do not skip any part of the story** — include every sentence.\n"
    #     "Now process this story:\n"
    #     + text
    # )
      

    try:
        logging.info("Starting data generation...")
        # Access target URL
        driver.get(TARGET_URL)
        time.sleep(6)
        textarea = driver.find_element(By.CSS_SELECTOR, '#userInput')
        textarea.click()
        driver.execute_script("""
        const el = document.querySelector('#userInput');
        if (el) {
            el.innerText = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    """, full_prompt)
        textarea.send_keys(Keys.ENTER)
        
        # Wait for critical content to load (adjust selector as needed)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "h2"))
        )
        
        # Additional delay for JavaScript rendering
        time.sleep(30)
        
        # Get page content
        page_content = driver.page_source
        soup = BeautifulSoup(driver.page_source, "html.parser")
        logging.info("Reached.... Searching code")

        # Find the <h2> tag with text "Copilot said"
        h2 = soup.find("h2", string=lambda t: t and "Copilot said" in t)
        if h2:
            # Find the first <pre><code> after the <h2> tag
            pre_code = None
            for sibling in h2.find_all_next():
                if sibling.name == "pre":
                    code_tag = sibling.find("code")
                    if code_tag:
                        pre_code = code_tag.get_text()
                        break

            if pre_code:
                # Save the JSON output
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    f.write(pre_code)
            else:
                print("❌ <pre><code> JSON output not found after <h2>.")
            print(f"✅ Saved content after <h2> with 'Copilot said' to {OUTPUT_FILE}")
            return OUTPUT_FILE
        else:
            print("❌ <h2> tag with text 'Copilot said' not found in the page content.")
            return None

    except Exception as e:
        logging.info(f"Error occurred: {str(e)}")
        
        return None

    finally:
        # Clean up
        driver.quit()
    return None

if __name__ == "__main__":
    generate_data()
