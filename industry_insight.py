import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v3.1", layout="wide")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 카테고리 구성
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC"],
    "식품": ["농/수/축산물", "가공식품", "음료", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "피트니스"],
    "생활/건강": ["주방용품", "생활용품", "반려동물", "의료기기"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 15px; border-left: 10px solid #FFB300; margin-bottom: 20px; line-height: 1.8; color: #333; font-size: 1.05em; }
    .keyword-label { color: #FFB300; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 AE Insight Pro v3.1")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 🌟 [v3.1 핵심] 광고주 설득용 고품질 키워드 추출 함수
def extract_high_quality_keywords(titles, industry):
    if not ai_engine: return " ".join(titles)
    try:
        prompt = f"""
        당신은 10년차 베테랑 광고 AE입니다. 다음 뉴스 데이터 {titles}를 기반으로 {industry} 업계의 제안서에 바로 쓸 수 있는 '날카로운 키워드'를 뽑으세요.
        
        [필수 포함 내용]
        1. 소비자의 숨은 욕구(Needs)나 결핍(Pain-point)을 나타내는 단어
        2. 요즘 인스타그램/유튜브에서 유행하는 밈이나 라이프스타일 키워드
        3. 단순 업종명(예: 골프)은 제외하고 구체적인 상품군이나 현상 위주 (예: '골린이 탈출', '야간 라운딩 패션')
        
        무의미한 조사, 일반 명사는 모두 제외하고 딱 15개의 유효 키워드만 콤마로 구분해서 대답하세요.
        """
        response = ai_engine.generate_content(prompt)
        return response.text.replace(',', ' ').replace('\n', ' ')
    except:
        return " ".join(titles)

def create_styled_wc(text, font_path):
    wc = WordCloud(
        font_path=font_path, width=1200, height=700,
        background_color='white', colormap='inferno',
        max_words=40, relative_scaling=0.6,
        prefer_horizontal=0.9
    ).generate(text)
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 AE용 전략 키워드 분석 (High-Quality)")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류", NAVER_CATEGORIES[m_cat])
    
    if st.button(f"🚀 {s_cat} 전략 리포트 추출"):
        with st.spinner("AI가 광고주 설득용 핵심 키워드를 선별 중입니다..."):
            # 뉴스 수집 범위를 넓힘
            queries = [f"{s_cat} 이슈", f"{s_cat} 소비자 반응", f"{s_cat} 신조어"]
            titles = []
            for q in queries:
                rss = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss); soup = BeautifulSoup(res.text, 'xml')
                titles.extend([i.title.get_text() for i in soup.find_all('item')[:10]])
            
            if titles:
                # 🌟 고품질 AI 키워드 추출
                hq_keywords = extract_high_quality_keywords(titles, s_cat)
                
                if ai_engine:
                    # 제안서에 복사해서 쓸 수 있는 요약 리포트
                    report_prompt = f"당신은 {s_cat} 업종 AE입니다. {titles}를 보고 광고주 제안서에 넣을 '시장 기회'와 '추천 카피'를 AE 말투로 작성해줘."
                    resp = ai_engine.generate_content(report_prompt)
                    st.markdown(f'<div class="ai-report-card"><b>💡 제안서 활용 포인트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                
                fig = create_styled_wc(hq_keywords, FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 전략 맵 저장", buf.getvalue(), f"{s_cat}_전략.png", "image/png")

# --- 나머지 메뉴 로직 ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 핵심 이슈 분석")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].dropna().unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('').astype(str))
            hq_words = extract_high_quality_keywords([text], f"{target} 소통")
            fig = create_styled_wc(hq_words, FONT_PATH)
            st.pyplot(fig)
            buf = BytesIO(); fig.savefig(buf, format="png")
            st.download_button("📥 분석 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")

elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 제안 솔루션")
    t_url = st.text_input("가망 광고주 URL")
    if st.button("💡 전략 도출"):
        brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
        resp = ai_engine.generate_content(f"광고주 {brand}를 위해 지금 바로 실행 가능한 마케팅 전략 3가지를 제안해줘.")
        st.markdown(f'<div class="ai-report-card">{resp.text}</div>', unsafe_allow_html=True)

elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리")
    up_f = st.file_uploader("💾 백업 데이터 로드 (XLSX)", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
        df.columns = [rename_map.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("데이터 로드 완료")
    st.dataframe(st.session_state.history_db, use_container_width=True)
