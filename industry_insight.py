import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.5", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (호환성 높은 모델명 고정)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
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

# 2. 상세 카테고리 구성 (네이버 데이터랩 기준)
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC", "영상/음향가전"],
    "식품": ["농/수/축산물", "반찬/가공식품", "음료", "과자/베이커리", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "헬스/요가", "수영/스포츠의류"],
    "가구/인테리어": ["침실/거실가구", "주방가구", "인테리어소품", "침구/커튼"],
    "생활/건강": ["주방/욕실용품", "세탁/생활용품", "반려동물", "의료기기/건강용품"]
}

# 세션 초기화 (데이터 휘발 방지 및 복구 데이터 저장용)
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 3. UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 12px; border-left: 10px solid #FFB300; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 4. 사이드바 메뉴
with st.sidebar:
    st.title("🚀 Industry Insight v1.5")
    st.markdown('<p class="menu-header">📋 메뉴 선택</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", 
        ["업종별 트렌드 체크", "가망 광고주 분석/제안", "광고주 DB/이력 관리", "소통 키워드 분석"],
        label_visibility="collapsed")

# --- [기능 1: 업종별 트렌드 체크] ---
if main_menu == "업종별 트렌드 체크":
    st.header("📈 업종별 이슈 마인드맵 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 (네이버 데이터랩)", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("상세 카테고리", NAVER_CATEGORIES[m_cat])
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner("최신 데이터 수집 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"전문 AE로서 {s_cat} 업종의 최근 트렌드 {titles}를 분석해 캠페인 전략 3가지를 제안해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 전략 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 응답 오류")
                
                wc = WordCloud(font_path=FONT_PATH, width=1000, height=600, background_color='white', colormap='tab10').generate(" ".join(titles))
                fig, ax = plt.subplots(figsize=(12, 7)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)

# --- [기능 2: 가망 광고주 분석/제안] ---
elif main_menu == "가망 광고주 분석/제안":
    st.header("🎯 URL 기반 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL 입력", placeholder="https://brand.naver.com/...")
    t_cat = st.selectbox("매칭 카테고리 선택", [f"{k} > {v}" for k, vv in NAVER_CATEGORIES.items() for v in vv])
    
    if st.button("💡 가망 광고주 제안 전략 생성"):
        if not t_url: st.warning("분석할 URL을 입력해 주세요.")
        else:
            with st.spinner("브랜드 및 시장 분석 중..."):
                # URL에서 브랜드 키워드 추출
                brand_name = t_url.split("//")[-1].split(".")[0]
                if "naver" in brand_name: brand_name = t_url.split("/")[-1]
                
                rss = f"https://news.google.com/rss/search?q={brand_name}+{t_cat.split(' > ')[1]}&hl=ko&gl=KR&ceid=KR:ko"
                news = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:10]]
                
                if ai_engine:
                    prompt = f"광고주: {brand_name}\nURL: {t_url}\n업종: {t_cat}\n관련뉴스: {news}\n\n위 정보를 바탕으로 1.현재 시장 위치 분석 2.업종 트렌드 결합 캠페인 전략 3.추천 매체 믹스를 제안해줘."
                    try:
                        resp = ai_engine.generate_content(prompt)
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand_name} 맞춤 제안서 초안</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 실패")

# --- [기능 3: 광고주 DB/이력 관리 (복구 및 입력)] ---
elif main_menu == "광고주 DB/이력 관리":
    st.header("📂 광고주 DB 및 실시간 소통 관리")
    
    # 1. 실시간 입력 섹션
    st.subheader("📝 실시간 소통 내용 입력")
    with st.form("history_input", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: client_name = st.text_input("광고주명")
        with col2: log_date = st.date_input("날짜", datetime.datetime.now())
        log_content = st.text_area("소통 상세 내용 (피드백, 요청사항 등)")
        log_kws = st.text_input("핵심 키워드 (쉼표 구분)")
        
        if st.form_submit_button("💾 소통 이력 저장"):
            new_row = pd.DataFrame([[log_date, client_name, log_content, log_kws]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
            st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
            st.success(f"{client_name} 이력이 저장되었습니다.")

    st.divider()
    
    # 2. 데이터 복구 섹션
    st.subheader("💾 기존 데이터 백업/복구")
    up_file = st.file_uploader("XLSX 백업 파일을 업로드하세요", type=['xlsx'])
    if up_file:
        try:
            # 업로드 즉시 세션 상태 업데이트
            st.session_state.history_db = pd.read_excel(up_file)
            st.success("✅ 기존 데이터 복구가 완료되었습니다!")
        except Exception as e: st.error(f"파일 로드 오류: {e}")

    if not st.session_state.history_db.empty:
        st.subheader("📋 전체 이력 리스트")
        st.dataframe(st.session_state.history_db, use_container_width=True)
        
        # 백업 파일 다운로드
        towrite = BytesIO()
        st.session_state.history_db.to_excel(towrite, index=False, engine='xlsxwriter')
        st.download_button(label="📥 현재 DB 백업본 다운로드", data=towrite.getvalue(), file_name="Industry_Insight_Backup.xlsx", mime="application/vnd.ms-excel")

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("관리 메뉴에서 데이터를 먼저 입력하거나 백업 파일을 업로드해 주세요.")
    else:
        target_client = st.selectbox("분석할 광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target_client]
        
        if not f_df.empty:
            st.subheader(f"🔍 {target_client} 소통 마인드맵 분석")
            full_text = " ".join(f_df['소통내용'].fillna('') + " " + f_df['핵심키워드'].fillna(''))
            if len(full_text.strip()) > 5:
                wc = WordCloud(font_path=FONT_PATH, width=1000, height=500, background_color='white', colormap='coolwarm').generate(full_text)
                fig, ax = plt.subplots(figsize=(12, 6)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
            else: st.warning("분석할 텍스트 내용이 부족합니다.")
