import streamlit as st
import folium
from folium.features import DivIcon
import streamlit.components.v1 as components
import math
import time
import random
import requests

# ==========================================
# 1. 코어 엔진: 하버사인 거리 계산 (방향 결정용)
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000 

# ==========================================
# 2. 가상 API 통신 (킥보드 데이터 생성)
# ==========================================
def fetch_live_kickboards(center_lat, center_lng, radius_m, count):
    kickboards = []
    degree_per_meter = 1 / 111000.0 
    for i in range(count):
        angle = random.uniform(0, 2 * math.pi)
        r = radius_m * math.sqrt(random.uniform(0.1, 1.0)) * degree_per_meter 
        lat = center_lat + r * math.cos(angle)
        lng = center_lng + (r * math.sin(angle)) / math.cos(math.radians(center_lat))
        kickboards.append({
            "id": f"KB-{random.randint(1000, 9999)}",
            "lat": lat,
            "lng": lng,
            "battery": random.randint(0, 15)
        })
    return kickboards

# ==========================================
# 3. 최적 경로 탐색 (Greedy TSP)
# ==========================================
def calculate_optimal_route(depot, kickboards):
    unvisited = kickboards.copy()
    current = depot
    path = []
    
    while unvisited:
        nearest = min(unvisited, key=lambda k: haversine(current['lat'], current['lng'], k['lat'], k['lng']))
        path.append(nearest)
        current = nearest
        unvisited.remove(nearest)
        
    return path

# ==========================================
# 4. [심화] OSRM 실제 도로망 API 호출
# ==========================================
def get_real_road_route(depot, path):
    """
    내비게이션 엔진(OSRM)에 방문할 좌표들을 보내서 '실제 도로를 따라가는 경로'를 받아옵니다.
    """
    # OSRM은 [경도(lng), 위도(lat)] 순서를 사용합니다.
    coords = [[depot["lng"], depot["lat"]]]
    for point in path:
        coords.append([point["lng"], point["lat"]])
        
    # 좌표들을 세미콜론(;)으로 연결하여 URL 생성
    coords_str = ";".join([f"{lon},{lat}" for lon, lat in coords])
    
    # OSRM API 호출 (Driving 모드, 전체 경로 반환, GeoJSON 포맷)
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(osrm_url)
        data = response.json()
        
        if data['code'] == 'Ok':
            # OSRM이 반환한 실제 도로망 위경도 리스트 (Folium에 맞게 lat, lng로 스왑)
            real_route_coords = [[lat, lon] for lon, lat in data['routes'][0]['geometry']['coordinates']]
            real_distance_m = data['routes'][0]['distance']
            return real_route_coords, real_distance_m
        else:
            return None, 0
    except Exception as e:
        st.error("도로망 데이터를 가져오는 중 오류가 발생했습니다.")
        return None, 0

# ==========================================
# 5. Streamlit 대시보드 UI
# ==========================================
st.set_page_config(page_title="제주 실사 라우팅 대시보드", layout="wide", page_icon="🌐")

JEJU_CITY_HALL = {"name": "제주시청 (수거 본부)", "lat": 33.4996213, "lng": 126.5311884}

st.sidebar.header("⚙️ 지오펜스(Geofence) 설정")
search_radius = st.sidebar.slider("수거 탐색 반경 (Meters)", min_value=300, max_value=2000, value=800, step=100)
kickboard_count = st.sidebar.slider("해당 구역 내 예상 방치 대수", min_value=5, max_value=25, value=10)
refresh_btn = st.sidebar.button("🔄 실시간 API 및 도로망 재탐색", use_container_width=True)

st.title("🌐 제주 스마트시티: AI 실제 도로망 라우팅 시스템")
st.markdown("건물을 뚫고 가는 단순 직선(Haversine) 경로의 한계를 극복하기 위해, **OSRM(Open Source Routing Machine) API**를 연동하여 실제 차량이 이동 가능한 도로망(Navigation Route) 기반 최적 동선을 생성합니다.")

if 'live_data' not in st.session_state or refresh_btn:
    with st.spinner('구역 내 전기자전거 데이터 수집 및 실제 도로망 경로를 연산 중입니다...'):
        # 1. 킥보드 데이터 수집
        st.session_state.live_data = fetch_live_kickboards(JEJU_CITY_HALL["lat"], JEJU_CITY_HALL["lng"], search_radius, kickboard_count)
        
        # 2. 알고리즘으로 방문 순서(Order) 결정
        start_calc = time.time()
        st.session_state.optimal_path = calculate_optimal_route(JEJU_CITY_HALL, st.session_state.live_data)
        
        # 3. [핵심] 결정된 순서대로 '실제 도로 경로' 추출
        st.session_state.real_route, st.session_state.total_dist = get_real_road_route(JEJU_CITY_HALL, st.session_state.optimal_path)
        st.session_state.calc_time = (time.time() - start_calc) * 1000

# 지표 출력
col1, col2, col3, col4 = st.columns(4)
col1.metric("탐색 반경", f"{search_radius} m")
col2.metric("수신된 전기자전거", f"{len(st.session_state.live_data)} 대")
if st.session_state.total_dist:
    col3.metric("실제 도로 주행 거리", f"{st.session_state.total_dist/1000:.2f} km")
col4.metric("AI + OSRM 연산 속도", f"{st.session_state.calc_time:.2f} ms")

# ==========================================
# 6. Folium 지도 렌더링
# ==========================================
m = folium.Map(location=[JEJU_CITY_HALL["lat"], JEJU_CITY_HALL["lng"]], zoom_start=15, tiles='CartoDB positron')

# 지오펜스 영역
folium.Circle(
    location=[JEJU_CITY_HALL["lat"], JEJU_CITY_HALL["lng"]],
    radius=search_radius, color='#3186cc', fill=True, fill_color='#3186cc', fill_opacity=0.1
).add_to(m)

# 제주시청 마커
folium.Marker(
    location=[JEJU_CITY_HALL["lat"], JEJU_CITY_HALL["lng"]],
    popup="<b>제주시청 (수거 트럭 출발)</b>",
    icon=folium.Icon(color="red", icon="building", prefix='fa')
).add_to(m)

# 킥보드 마커 그리기
for i, kb in enumerate(st.session_state.optimal_path):
    icon_html = f'''<div style="font-family: Arial; font-size: 12px; font-weight: bold; color: white; background-color: #2c3e50;
            border: 2px solid white; border-radius: 50%; width: 24px; height: 24px; text-align: center;
            line-height: 20px; box-shadow: 1px 1px 3px rgba(0,0,0,0.5);">{i+1}</div>'''
    
    folium.Marker(
        location=[kb["lat"], kb["lng"]],
        icon=DivIcon(html=icon_html),
        tooltip=f"<b>수거 순서: {i+1}</b><br>기기: {kb['id']}<br>배터리: {kb['battery']}%"
    ).add_to(m)

# [핵심] 직선이 아닌 '실제 도로망' PolyLine 그리기
if st.session_state.real_route:
    folium.PolyLine(
        locations=st.session_state.real_route,
        color="#8E44AD", # 세련된 보라색 라인
        weight=5, 
        opacity=0.8
    ).add_to(m)

components.html(m._repr_html_(), height=650)