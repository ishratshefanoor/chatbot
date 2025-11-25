import requests                      #requests - Fetches data from websites (makes HTTP requests)
from bs4 import BeautifulSoup        #bs4 - This imports the BeautifulSoup tool so you we extract text and elements from an HTML webpage
import time                          #time - Adds delays between operations
import json                          #json - Saves and loads data in JSON file format
import re                            #re - Uses regex to find phone numbers, emails, and patterns
from difflib import SequenceMatcher  #from difflib - This loads the Python module that contains tools for finding differences between texts,  
                                     #import SequenceMatcher - This imports the specific class that checks how similar two strings or sentences are.



#1. URL LIST

URLS = [
    "https://www.kryzo.tech/about",
    "https://www.kryzo.tech/service",
    "https://www.kryzo.tech/contact",
    "https://www.kryzo.tech/blogs"
]



#2. CLEAN TEXT FILTER

def clean_text(paragraphs):
    cleaned = []
    skip_words = {"about", "service", "services", "contact", "blogs", "registration"}

    for p in paragraphs:
        p_low = p.lower().strip()
        if p_low in skip_words:
            continue
        if len(p_low.split()) < 4:
            continue
        cleaned.append(p)

    return cleaned



#3. SCRAPER FUNCTION

def scrape_page(url):
    print(f"Scraping {url} ...")

    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except:
        print("Error loading:", url)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    paragraphs = []

    for tag in soup.find_all(['p','h1','h2','h3']):
        txt = tag.get_text(" ", strip=True)
        if txt and len(txt) > 10:
            paragraphs.append(txt)

    paragraphs = list(dict.fromkeys(paragraphs))
    paragraphs = clean_text(paragraphs)

    return {"url": url, "paragraphs": paragraphs}



#4. SCRAPE ALL PAGES

scraped_data = []
for url in URLS:
    d = scrape_page(url)
    if d:
        scraped_data.append(d)
    time.sleep(1)

with open("scraped_pages.json","w",encoding="utf-8") as f:
    json.dump(scraped_data, f, indent=4, ensure_ascii=False)

print("\nScraping complete!")


#5. NORMALIZER → Fix greetings + slang

def normalize(text):
    t = text.lower().strip()
    t = t.replace("?", "").replace("!", "").replace(".", "")
    t = t.replace("  ", " ")

    if t.replace(" ", "") in ["hru","h r u","hr u"]:
        return "how are you"

    if t in ["kamon acho","kemon acho"]:
        return "how are you"

    return t


#6. DETECT ABOUT & SERVICES QUESTIONS

def is_about_question(q):
    keys = ["about", "company", "kryzo", "about us", "details"]
    return any(k in q for k in keys)

def is_service_question(q):
    keys = ["service","services","provide","offer","ki service","solutions"]
    return any(k in q for k in keys)



#7. EXTRACT SERVICES LIST

def extract_services_from_page(page):
    services = []
    keywords = ["service","solution","development","application","web","mobile","software"]

    for para in page["paragraphs"]:
        if len(para) > 400:
            continue  # ignore blog-like

        low = para.lower()
        if any(k in low for k in keywords):

            parts = re.split(r"[•\-\n]", para)
            for p in parts:
                p = p.strip()
                if len(p) > 5 and any(k in p.lower() for k in keywords):
                    services.append(p)

    services = list(dict.fromkeys(services))
    return services



#8. ANSWER ENGINE

phone_pattern = re.compile(r'\+?\d[\d\s-]{7,}\d')
email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')


def find_answer(question, pages):
    q = normalize(question)

    # ---------- GREETINGS ----------
    if q in ["hi","hello","hey"]:
        return "Hello! How can I help you?"

    if q == "how are you":
        return "I'm great! 😊 What about you?"

    if q in ["good","fine","great","cool"]:
        return "Nice! How can I help you?"


    # ---------- PHONE ----------
    if any(k in q for k in ["phone","number","contact number"]):
        phones = []
        for p in pages:
            for para in p["paragraphs"]:
                phones.extend(phone_pattern.findall(para))
        if phones:
            return "Phone Number:\n" + "\n".join("• "+ph for ph in phones)
        return "No phone number found."


    # ---------- EMAIL ----------
    if "email" in q or "mail" in q:
        emails = []
        for p in pages:
            for para in p["paragraphs"]:
                emails.extend(email_pattern.findall(para))
        if emails:
            return "Email Address:\n" + "\n".join("• "+em for em in emails)
        return "No email found."


    # ---------- ABOUT ----------
    if is_about_question(q):
        for page in pages:
            if "about" in page["url"]:
                for para in page["paragraphs"]:
                    if len(para) < 350:
                        return para
        return "We are a digital service company helping businesses grow with modern technology."


    # ---------- SERVICES (LIST MODE) ----------
    if is_service_question(q):
        for page in pages:
            if "service" in page["url"]:
                service_list = extract_services_from_page(page)
                if service_list:
                    result = "Here are the services we provide:\n\n"
                    for s in service_list:
                        result += "• " + s + "\n"
                    return result.strip()

        return "We provide multiple digital services."


    # ---------- GENERAL SEARCH ----------
    words = set(re.findall(r"\w+", q))
    best = ""
    best_score = 0

    for page in pages:
        for para in page["paragraphs"]:
            score = len(words & set(re.findall(r"\w+", para.lower())))
            if score > best_score:
                best_score = score
                best = para

    return best if best else "Sorry, I couldn't find relevant information."



#9. CHAT LOOP

while True:
    user = input("\nYou: ").strip()
    if user.lower() == "exit":
        print("Bot: Bye! 😊")
        break

    ans = find_answer(user, scraped_data)
    print("Bot:", ans)

