import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
import numpy as np
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.7", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (호환성 에러 방지 로직)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # v1beta 환경에서도 가장 안정적으로 응답하는 모델명으로 고정
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        try:
            return genai.GenerativeModel('gemini-pro')
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

# 네이버 데이터랩 기준 카테고리 구성
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "IT기기"],
    "식품": ["가공식품", "신선식품", "음료", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "피트니스"],
    "생활/건강": ["주방/욕실", "생활용품", "반려동물", "의료기기"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일 (마인드맵 비주얼 강조)
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F0F7FF; border-radius: 15px; border-left: 8px solid #007BFF; margin-bottom: 20px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v1.7")
    st.markdown('<p class="menu-header">📋 메인 메뉴</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"], label_visibility="collapsed")

# 🌟 마인드맵 스타일 시각화 함수 (원형 구조)
def create_mindmap(text, font_path, colormap='tab20'):
    x, y = np.ogrid[:1000, :1000]
    mask = (x - 500) ** 2 + (y - 500) ** 2 > 450 ** 2
    mask = 255 * mask.astype(int)
    
    wc = WordCloud(
        font_path=font_path, width=1000, height=1000,
        background_color='white', mask=mask,
        colormap=colormap, prefer_horizontal=0.6,
        relative_scaling=0.5, min_font_size=15
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업계 이슈 마인드맵 리포트")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("상세 카테고리", NAVER_CATEGORIES[m_cat])
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner("최신 트렌드 분석 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"{s_cat} 업종 트렌드 분석 및 캠페인 소구점 제안:\n" + "\n".join(titles))
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 이슈 브리핑</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 모델 연결 실패. 잠시 후 다시 시도해 주세요.")
                
                fig = create_mindmap(" ".join(titles), FONT_PATH, 'Paired')
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 마인드맵 저장", buf.getvalue(), f"{s_cat}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 분석] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 URL 기반 가망 광고주 제안")
    t_url = st.text_input("가망 광고주 URL", placeholder="https://...")
    t_cat = st.selectbox("매칭 카테고리", [f"{k} > {v}" for k, vv in NAVER_CATEGORIES.items() for v in vv])
    
    if st.button("💡 제안 전략 도출"):
        if not t_url: st.warning("URL을 입력해 주세요.")
        else:
            with st.spinner("브랜드 현황 및 트렌드 매칭 중..."):
                brand = t_url.split("//")[-1].split(".")[0]
                if "naver" in t_url: brand = t_url.split("/")[-1]
                
                rss = f"https://news.google.com/rss/search?q={brand}+{t_cat.split(' > ')[1]}&hl=ko&gl=KR&ceid=KR:ko"
                news = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:12]]
                
                if ai_engine:
                    try:
                        prompt = f"광고주: {brand}, 업종: {t_cat}, 이슈: {news}. AE로서 1.브랜드진단 2.트렌드전략 3.추천매체를 상세히 제안해."
                        resp = ai_engine.generate_content(prompt)
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand} 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 오류가 발생했습니다.")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 관리 및 복구")
    with st.expander("📝 소통 내용 기록하기"):
        with st.form("input_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("광고주명")
            date = c2.date_input("날짜", datetime.date.today())
            content = st.text_area("내용")
            tag = st.text_input("키워드")
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[date, name, content, tag]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.success("저장되었습니다.")

    st.divider()
    up_f = st.file_uploader("💾 백업 파일 복구 (XLSX)", type=['xlsx'])
    if up_f:
        try:
            st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
            st.success("✅ 기존 데이터 복구가 완료되었습니다!")
        except: st.error("파일 로드 실패")
    
    if not st.session_state.history_db.empty:
        st.dataframe(st.session_state.history_db, use_container_width=True)
        towrite = BytesIO()
        st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("📥 DB 백업 다운로드", towrite.getvalue(), "Industry_Backup.xlsx")

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 키워드 마인드맵")
    if st.session_state.history_db.empty:
        st.info("데이터를 먼저 입력하거나 복구하세요.")
    else:
        target = st.selectbox("분석할 광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        period = st.select_slider("분석 기간 설정 (최근 n일)", options=[7, 30, 90, 180, 365], value=90)
        
        df = st.session_state.history_db.copy()
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        limit_date = datetime.date.today() - datetime.timedelta(days=period)
        f_df = df[(df['광고주명'] == target) & (df['날짜'] >= limit_date)]
        
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('') + " " + f_df['핵심키워드'].fillna(''))
            if len(text.strip()) > 5:
                fig = create_mindmap(text, FONT_PATH, 'coolwarm')
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 마인드맵 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")
