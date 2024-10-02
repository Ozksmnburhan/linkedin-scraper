import streamlit as st
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Airtable credentials
AIRTABLE_BASE_ID = 'appCIHUNjRGLIw3uh'
AIRTABLE_API_KEY = 'patb6iSnO3urlCr64.edde605fb847c133eb55fbdd6907b050eb3a31198f16fecee3b781d5dd751642'
AIRTABLE_TABLE_NAME = 'py-to-airtable'

# Airtable endpoint
endpoint = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'

# Function to install and set up `geckodriver`
@st.experimental_singleton
def install_geckodriver():
    os.system('sbase install geckodriver')
    os.system('ln -s /home/appuser/venv/lib/python3.7/site-packages/seleniumbase/drivers/geckodriver /home/appuser/venv/bin/geckodriver')

_ = install_geckodriver()

def login_to_linkedin(driver, username, password):
    driver.get('https://www.linkedin.com/login')
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'username')))
    username_input = driver.find_element(By.ID, 'username')
    password_input = driver.find_element(By.ID, 'password')
    username_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'global-nav__me')))

def get_company_info(driver, company_name, company_url):
    driver.get(company_url)
    WebDriverWait(driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    time.sleep(2)  # Ensure the page is fully loaded

    company_info = {
        "Name": company_name,
        "URL": company_url,
        "Description": "N/A",
        "Website": "N/A",
        "Area": "N/A",
        "Founded": "N/A",
        "Headquarters": "N/A"
    }

    try:
        description = driver.find_element(By.CSS_SELECTOR, 'section.artdeco-card p.break-words').text
        company_info["Description"] = description
    except Exception as e:
        st.write(f"Description not found: {e}")

    try:
        website = driver.find_element(By.CSS_SELECTOR, 'dd a.link-without-visited-state').get_attribute('href')
        company_info["Website"] = website
    except Exception as e:
        st.write(f"Website not found: {e}")

    try:
        area = driver.find_element(By.CSS_SELECTOR, 'div.org-top-card-summary-info-list__info-item').text.split(",")[0]
        company_info["Area"] = area
    except Exception as e:
        st.write(f"Area not found: {e}")

    try:
        founded_text = driver.find_element(By.CSS_SELECTOR, 'dl.overflow-hidden').text
        if "Founded" in founded_text:
            start_index = founded_text.index("Founded") + len("Founded ")
            founded_year = founded_text[start_index:start_index + 4]
            company_info["Founded"] = founded_year
    except Exception as e:
        st.write(f"Founded year not found: {e}")

    try:
        headquarters_text = driver.find_element(By.CSS_SELECTOR, 'dl.overflow-hidden').text
        if "Headquarters" in headquarters_text:
            start_index = headquarters_text.index("Headquarters") + len("Headquarters ")
            headquarters_city = headquarters_text[start_index:].split('\n')[0]
            company_info["Headquarters"] = headquarters_city
    except Exception as e:
        st.write(f"Headquarters not found: {e}")

    return company_info

def add_to_airtable(company_info):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "records": [
            {
                "fields": {
                    "Şirket İsmi": company_info["Name"],
                    "Web Sitesi": company_info["Website"],
                    "Area": company_info["Area"],
                    "Kuruluş Yılı": company_info["Founded"],
                    "Merkez": company_info["Headquarters"]
                }
            },
        ]
    }
    r = requests.post(endpoint, json=data, headers=headers)
    return r.status_code == 200

def create_pdf(company_info):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    c.setFont('DejaVuSans', 16)
    text_x = 50
    y_position = 750

    c.drawString(text_x, y_position, f"Company Name: {company_info['Name']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"URL: {company_info['URL']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Website: {company_info['Website']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Area: {company_info['Area']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Founded: {company_info['Founded']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Headquarters: {company_info['Headquarters']}")

    description_lines = company_info['Description'].split("\n")
    for line in description_lines:
        c.drawString(text_x, y_position, line)
        y_position -= 20

    c.save()
    buffer.seek(0)
    return buffer

def main():
    st.title("LinkedIn Company Information Scraper")

    linkedin_username = st.text_input("LinkedIn Username")
    linkedin_password = st.text_input("LinkedIn Password", type="password")
    company_name = st.text_input("Company Name")
    company_url = st.text_input("Company URL (Optional)")
    search_button = st.button("Search for Company Info")
    airtable_button = st.button("Upload to Airtable")

    if 'driver' not in st.session_state:
        st.session_state.driver = None

    if 'collected_company_info' not in st.session_state:
        st.session_state.collected_company_info = None

    if search_button:
        if linkedin_username and linkedin_password and company_name:
            try:
                if not st.session_state.driver:
                    opts = Options()
                    opts.add_argument("--headless")
                    driver = webdriver.Firefox(options=opts)
                    st.session_state.driver = driver

                login_to_linkedin(st.session_state.driver, linkedin_username, linkedin_password)

                if not company_url:
                    company_url = f"https://www.linkedin.com/company/{company_name.lower()}/about/"

                company_info = get_company_info(st.session_state.driver, company_name, company_url)
                st.session_state.collected_company_info = company_info

                st.write("Company Information:")
                st.write(company_info)
            except Exception as e:
                st.error(f"An error occurred: {e}")

        else:
            st.error("Please enter LinkedIn username, password, and company name.")

    if st.session_state.collected_company_info:
        pdf_buffer = create_pdf(st.session_state.collected_company_info)
        sanitized_company_name = st.session_state.collected_company_info['Name'].replace(' ', '_')
        st.download_button(
            label="Download PDF",
            data=pdf_buffer,
            file_name=f"{sanitized_company_name}.pdf",
            mime='application/pdf'
        )

    if airtable_button and st.session_state.collected_company_info:
        success = add_to_airtable(st.session_state.collected_company_info)
        if success:
            st.success("Company information successfully uploaded to Airtable.")
        else:
            st.error("Error uploading company information to Airtable.")

if __name__ == "__main__":
    main()

"""import streamlit as st  # çalışan chrome driver kodu
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import requests
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from textwrap import wrap
from webdriver_manager.chrome import ChromeDriverManager

# Airtable bilgileri hesaba göre düzenlenecek.
AIRTABLE_BASE_ID = 'appCIHUNjRGLIw3uh'
AIRTABLE_YOUR_SECRET_API_TOKEN = 'patb6iSnO3urlCr64.edde605fb847c133eb55fbdd6907b050eb3a31198f16fecee3b781d5dd751642'
AIRTABLE_TABLE_NAME = 'py-to-airtable'

endpoint = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'

def login_to_linkedin(driver, username, password):
    driver.get('https://www.linkedin.com/login')
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'username')))
    username_input = driver.find_element(By.ID, 'username')
    password_input = driver.find_element(By.ID, 'password')
    username_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'global-nav__me')))

def get_company_info(driver, company_name, company_url):
    driver.get(company_url)
    WebDriverWait(driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    time.sleep(2)  # Sayfanın tamamen yüklenmesi için ek süre

    company_info = {
        "Name": company_name,
        "URL": company_url,
        "Description": "N/A",
        "Website": "N/A",
        "Area": "N/A",
        "Founded": "N/A",
        "Headquarters": "N/A"
    }

    try:
        description = driver.find_element(By.CSS_SELECTOR, 'section.artdeco-card p.break-words').text
        company_info["Description"] = description
    except Exception as e:
        st.write(f"Açıklama bulunamadı: {e}")

    try:
        website = driver.find_element(By.CSS_SELECTOR, 'dd a.link-without-visited-state').get_attribute('href')
        company_info["Website"] = website
    except Exception as e:
        st.write(f"Web sitesi bulunamadı: {e}")

    try:
        area = driver.find_element(By.CSS_SELECTOR, 'div.org-top-card-summary-info-list__info-item').text.split(",")[0]
        company_info["Area"] = area
    except Exception as e:
        st.write(f"Alan bulunamadı: {e}")

    try:
        # Metni bul
        founded_text = driver.find_element(By.CSS_SELECTOR, 'dl.overflow-hidden').text

        # 'Founded' veya 'Kuruluş Yılı' anahtar kelimesini bul ve sonrasındaki yılı çıkar
        if "Founded" in founded_text:
            start_index = founded_text.index("Founded") + len("Founded ")
            founded_year = founded_text[start_index:start_index + 4]
            company_info["Founded"] = founded_year
        elif "Kuruluş" in founded_text:
            start_index = founded_text.index("Kuruluş") + len("Kuruluş ")
            founded_year = founded_text[start_index:start_index + 4]
            company_info["Founded"] = founded_year
        else:
            company_info["Founded"] = "Founded veya Kuruluş Yılı bilgisi bulunamadı"
    except Exception as e:
        st.write(f"Kuruluş yılı bulunamadı: {e}")

    try:
        # Metni bul
        headquarters_text = driver.find_element(By.CSS_SELECTOR, 'dl.overflow-hidden').text

        # 'Headquarters' veya 'Genel Merkez' anahtar kelimesini bul ve sonrasındaki şehri çıkar
        if "Headquarters" in headquarters_text:
            start_index = headquarters_text.index("Headquarters") + len("Headquarters ")
            # Headquarters bilgisinin bulunduğu satırı ayır
            headquarters_city = headquarters_text[start_index:].split('\n')[0]
            company_info["Headquarters"] = headquarters_city
        elif "Genel Merkez" in headquarters_text:
            start_index = headquarters_text.index("Genel Merkez") + len("Genel Merkez ")
            # Genel Merkez bilgisinin bulunduğu satırı ayır
            headquarters_city = headquarters_text[start_index:].split('\n')[0]
            company_info["Headquarters"] = headquarters_city
        else:
            company_info["Headquarters"] = "Headquarters veya Genel Merkez bilgisi bulunamadı"
    except Exception as e:
        st.write(f"Merkez şehir bilgisi bulunamadı: {e}")

    return company_info

# Fields kısmı, Table başlıklarına özel olarak düzenlenecek.
def add_to_airtable(company_info):
    if company_info.get("Name") is None:
        return
    headers = {
        "Authorization": f"Bearer {AIRTABLE_YOUR_SECRET_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "records": [
            {
                "fields": {
                    "Şirket İsmi": company_info["Name"],
                    "Web Sitesi": company_info["Website"],
                    "Area": company_info["Area"],
                    "Kuruluş Yılı": company_info["Founded"],
                    "Merkez": company_info["Headquarters"]
                }
            },
        ]
    }
    r = requests.post(endpoint, json=data, headers=headers)
    return r.status_code == 200

def create_pdf(company_info):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    logo_path = 'logo-2.png'
    logo_width = 150
    logo_height = 75
    logo_margin = 30

    logo_x = 50
    logo_y = height - logo_height - logo_margin

    c.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height)

    c.setFont('DejaVuSans', 16)
    text_x = logo_x - 20
    y_position = logo_y - 40

    c.setFillColor(colors.darkblue)
    c.drawString(text_x, y_position, f"İsim: {company_info['Name']}")
    y_position -= 25

    c.setFont('DejaVuSans', 12)
    c.setFillColor(colors.black)
    c.drawString(text_x, y_position, f"URL: {company_info['URL']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Web Sitesi: {company_info['Website']}")
    y_position -= 20
    c.drawString(text_x, y_position, f"Alan: {company_info['Area']}")
    y_position -= 20

    c.setFillColor(colors.black)
    c.setFont('DejaVuSans', 12)
    c.drawString(text_x, y_position, "Açıklama:")
    y_position -= 15

    description_lines = wrap(company_info['Description'], width=90)
    for line in description_lines:
        c.drawString(text_x, y_position, line)
        y_position -= 15

    c.save()
    buffer.seek(0)
    return buffer

def main():
    st.title("LinkedIn Şirket Bilgileri Toplama")

    linkedin_username = st.text_input("LinkedIn Kullanıcı Adı")
    linkedin_password = st.text_input("LinkedIn Şifre", type="password")
    company_name = st.text_input("Şirket İsmi")
    company_url = st.text_input("Şirket URL (Opsiyonel)")
    search_button = st.button("Şirket Bilgilerini Ara")
    airtable_button = st.button("Airtable'a yükle")

    if 'driver' not in st.session_state:
        st.session_state.driver = None

    if 'collected_company_info' not in st.session_state:
        st.session_state.collected_company_info = None

    if search_button:
        if linkedin_username and linkedin_password and company_name:
            if not st.session_state.driver:
                try:
                    service = Service(ChromeDriverManager(version="129.0.6668.89").install()),options=options                     
                    options = Options()
                    options.headless = True
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    driver = webdriver.Chrome(service=service, options=options)
                    driver.implicitly_wait(2)
                    st.session_state.driver = driver
                    login_to_linkedin(driver, linkedin_username, linkedin_password)
                except ValueError as e:
                    st.error(f"ChromeDriver yüklenirken hata oluştu: {str(e)}")
                    st.info("Manuel ChromeDriver kurulumu deneyin ve yolunu belirtin:")
                    chromedriver_path = st.text_input("ChromeDriver yolu:")
                    if chromedriver_path:
                        try:
                            service = Service(chromedriver_path)
                            driver = webdriver.Chrome(service=service, options=options)
                            driver.implicitly_wait(2)
                            st.session_state.driver = driver
                            login_to_linkedin(driver, linkedin_username, linkedin_password)
                        except Exception as e:
                            st.error(f"Manuel ChromeDriver kurulumunda hata: {str(e)}")
                            return
                except Exception as e:
                    st.error(f"Beklenmeyen bir hata oluştu: {str(e)}")
                    return

            driver = st.session_state.driver

            if not company_url:
                company_url = f"https://www.linkedin.com/company/{company_name.lower()}/about/"

            company_info = get_company_info(driver, company_name, company_url)
            st.session_state.collected_company_info = company_info

            st.write("Şirket Bilgileri:")
            st.write(f"İsim: {company_info['Name']}")
            st.write(f"URL: {company_info['URL']}")
            st.write(f"Açıklama: {company_info['Description']}")
            st.write(f"Web Sitesi: {company_info['Website']}")
            st.write(f"Alan: {company_info['Area']}")
            st.write(f"Kuruluş Yılı: {company_info['Founded']}")
            st.write(f"Merkez: {company_info['Headquarters']}")
            st.write("-" * 40)

        else:
            st.error("Lütfen LinkedIn kullanıcı adı, şifre ve şirket ismi girin.")

    if st.session_state.collected_company_info:
        pdf_buffer = create_pdf(st.session_state.collected_company_info)
        sanitized_company_name = st.session_state.collected_company_info['Name'].replace(' ', '_')
        st.download_button(
            label="PDF İndir",
            data=pdf_buffer,
            file_name=f"{sanitized_company_name}.pdf",
            mime='application/pdf'
        )

    if airtable_button:
        company_info = st.session_state.collected_company_info
        if company_info:
            success = add_to_airtable(company_info)
            if success:
                st.success("Bilgiler Airtable'a başarıyla yüklendi.")
            else:
                st.error("Bilgiler Airtable'a yüklenirken bir hata oluştu.")

if __name__ == "__main__":
    main()"""
