import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# ฐานข้อมูลความเร็วลม มยผ. 1311-50
# ==========================================
PROVINCE_V = {
    "กรุงเทพฯ / นนทบุรี / ปทุมธานี / สมุทรปราการ / สมุทรสาคร (25 m/s)": 25.0,
    "ชลบุรี / ระยอง / จันทบุรี / ตราด (30 m/s)": 30.0,
    "ภูเก็ต / พังงา / กระบี่ (27 m/s)": 27.0,
    "เชียงใหม่ / เชียงราย / พิษณุโลก / แม่ฮ่องสอน (25 m/s)": 25.0,
    "นครราชสีมา / ขอนแก่น / อุดรธานี / อุบลราชธานี (25 m/s)": 25.0,
    "สงขลา / สุราษฎร์ธานี / นครศรีธรรมราช (25 m/s)": 25.0,
    "🛠️ กำหนดค่าความเร็วลมเอง (Manual Input)": 25.0
}

# ==========================================
# Core Logic & Math
# ==========================================
def calculate_q(V):
    rho = 1.25  
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665  

def get_Ce_details(z, exposure):
    z_eff = max(z, 6.0) 
    if 'A' in exposure:
        alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure:
        alpha, min_val, max_val = 0.28, 0.7, 1.2
    else:
        alpha, min_val, max_val = 0.40, 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"สูตรภูมิประเทศ {exposure[:1]}: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมด้วยค่าที่ {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจาก z = {z} ม. ต่ำกว่าขั้นต่ำ (6.0 ม.) ให้ใช้ z = 6.0 ม. | " + explanation
    return ce, explanation

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer (มยผ. 1311-50 / 1302)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิ, พื้นที่รับแรงดัน (Tributary Area) และเปรียบเทียบแรงเฉือนฐานแผ่นดินไหว</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงลม")

st.sidebar.subheader("1. ข้อมูลสถานที่ตั้งและการ Auto-V")
prov_choice = st.sidebar.selectbox("พื้นที่ตั้งอาคาร (ความเร็วลมตามมาตรฐาน)", list(PROVINCE_V.keys()))

if "Manual Input" in prov_choice:
    V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
else:
    V_input = PROVINCE_V[prov_choice]
    st.sidebar.info(f"ระบบเลือกใช้ V = {V_input} m/s อัตโนมัติ")

exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0)

# --- [NEW] ที่มาของแผ่นดินไหว ---
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. ที่มาของแรงแผ่นดินไหว (V_EQ)")
eq_mode = st.sidebar.radio("วิธีการหาค่าแรงแผ่นดินไหว", ["กรอกค่าเองโดยตรง (Direct Input)", "ให้โปรแกรมช่วยประมาณการอย่างง่าย (มยผ. 1302)"])

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์รูปทรงอาคาร")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อมของอาคาร", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)

Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)
Cp_s = st.sidebar.number_input("Cp ผนังด้านข้าง (Sidewall)", value=-0.7, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Flat Roof)", value=-0.7, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

col_b, col_l, col_n = st.columns(3)
with col_b: B = st.number_input("ความกว้างอาคารแนวขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l: L = st.number_input("ความยาวอาคารแนวตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n: num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", value=3, min_value=1, step=1)

with st.expander("📐 ปรับแต่งความสูงแยกแต่ละชั้น", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        col_idx = i % 4
        default_h = 4.0 if i == 0 else 3.5 
        with floor_cols[col_idx]:
            h_val = st.number_input(f"ความสูงชั้นที่ {i+1} (ม.)", value=default_h, min_value=1.0, step=0.1, key=f"h_f_{i}")
            floor_heights.append(h_val)

H_total = sum(floor_heights)

# คำนวณแผ่นดินไหวตามโหมดที่เลือก
if eq_mode == "กรอกค่าเองโดยตรง (Direct Input)":
    V_EQ_calculated = st.sidebar.number_input("ระบุแรงเฉือนฐานแผ่นดินไหว V_EQ (kN)", value=120.0, step=10.0)
    eq_source_text = "ใช้ค่าแรงเฉือนฐานแผ่นดินไหวที่ได้จากการคำนวณภายนอกโดยตรง"
else:
    st.sidebar.markdown("**🧮 ประมาณการน้ำหนักอาคารรวม (W)**")
    w_dl_ll = st.sidebar.number_input("น้ำหนักบรรทุกคงที่+จรเฉลี่ยรายชั้น (kgf/m²)", value=600.0, step=50.0)
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แรงแผ่นดินไหว Cs", value=0.05, step=0.01, format="%.3f")
    
    # น้ำหนักตึกรวม W = พื้นที่อาคาร (B*L) * จำนวนชั้น * น้ำหนักต่อตรม.
    W_building_kgf = (B * L) * num_stories * w_dl_ll
    W_building_kN = W_building_kgf * 0.00980665
    V_EQ_calculated = cs_coeff * W_building_kN
    
    st.sidebar.info(f"น้ำหนักตึกรวม W = {W_building_kN:.1f} kN\n(สูตร: Cs * W)")
    st.sidebar.success(f"คำนวณแผ่นดินไหวได้ V_EQ = {V_EQ_calculated:.1f} kN")
    eq_source_text = f"ประมาณการตาม มยผ. 1302: น้ำหนักโครงสร้างรวม W = {W_building_kN:.1f} kN, เลือกใช้สัมประสิทธิ์แรงแผ่นดินไหว Cs = {cs_coeff:.3f} ทำให้ออกมาเป็นแรงเฉือนฐานแผ่นดินไหวสถิตเทียบเท่า $V_{{EQ}} = C_s \\times W = {V_EQ_calculated:.2f}$ kN"

# --- [ENGINE CHECKER]: ตรวจสอบคุณสมบัติอาคารไหวตัวง่าย ---
slenderness = H_total / B
if H_total > 40.0 or slenderness > 4.0:
    st.warning(f"⚠️ **คำเตือนทางวิศวกรรม (มยผ. 1311-50):** อาคารนี้เข้าข่ายเป็น **'อาคารไหวตัวง่าย (Flexible Building)'** เนื่องจากความสูง H ({H_total:.2f} ม.) > 40 ม. หรือ อัตราส่วนความเพรียว H/B ({slenderness:.2f}) > 4 มาตรฐานกำหนดให้ต้องคำนวณค่าประกอบลมกระโชก ($C_g$) ด้วยวิธีพลศาสตร์อย่างละเอียด ห้ามตรึงค่าคงที่ที่ 2.0")

# ==========================================
# Engine Core Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_roof_ext = Iw_input * qh * Cg_input * Cp_r
p_internal_pos = qh * GCpi     
p_internal_neg = qh * (-GCpi)  

net_roof_case1 = p_roof_ext - p_internal_neg
net_roof_case2 = p_roof_ext - p_internal_pos
net_l_case1 = p_leeward - p_internal_neg  
net_l_case2 = p_leeward - p_internal_pos  

z_cumulative = 0
floors_data = []

for i in range(num_stories):
    h_current = floor_heights[i]
    z_bottom = z_cumulative
    z_top = z_cumulative + h_current
    z_mid = (z_bottom + z_top) / 2.0 
    
    Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
    p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
    p_s_z = Iw_input * q * Ce_mid * Cg_input * Cp_s  
    
    net_w_case1 = p_w_z - p_internal_neg
    net_w_case2 = p_w_z - p_internal_pos
    net_s_case1 = p_s_z - p_internal_neg
    net_s_case2 = p_s_z - p_internal_pos
    
    # [Tributary Area] พื้นที่รับลมแผ่รายชั้น
    trib_area_front = L * h_current  # ด้านหน้าตั้งฉากลม
    trib_area_side = B * h_current   # ด้านข้างขนานลม
    
    # Story Force (kN) 
    f_story_kgf_c1 = (net_w_case1 + abs(net_l_case1)) * trib_area_front
    f_story_kn_c1 = f_story_kgf_c1 * 0.00980665
    
    f_story_kgf_c2 = (net_w_case2 + abs(net_l_case2)) * trib_area_front
    f_story_kn_c2 = f_story_kgf_c2 * 0.00980665
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_mid_exp, "p_windward": p_w_z, "p_sidewall_ext": p_s_z,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2,
        "net_s_case1": net_s_case1, "net_s_case2": net_s_case2,
        "trib_area_front": trib_area_front, "trib_area_side": trib_area_side,
        "f_story_kn_c1": f_story_kn_c1, "f_story_kn_c2": f_story_kn_c2
    })
    z_cumulative = z_top

V_wind_case1 = sum([f['f_story_kn_c1'] for f in floors_data])
V_wind_case2 = sum([f['f_story_kn_c2'] for f in floors_data])
V_wind_max = max(V_wind_case1, V_wind_case2)

# ==========================================
# PLOTLY PLOTTING LOGIC
# ==========================================
def plot_cross_section_full(floors, view_mode):
    fig = go.Figure()
    # วาดตัวอาคาร
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30, 58, 138, 0.03)", line=dict(color="#1E3A8A", width=3), name="อาคาร"))
    
    # วาดลูกศรแรงดันรายชั้นฝั่งรับลม
    for f in floors:
        val_w = f['p_windward'] if view_mode == "External" else (f['net_w_case1'] if view_mode == "Case 1" else f['net_w_case2'])
        arrow_len = 1.5 + abs(val_w) / 40.0
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_len, ay=f['z_mid'], text=f"<b>{val_w:.1f}</b>", showarrow=True, arrowhead=2, arrowcolor="#DC2626")
        
    # วาดแรงลมตามลม (Leeward)
    val_l = p_leeward if view_mode == "External" else (net_l_case1 if view_mode == "Case 1" else net_l_case2)
    fig.add_annotation(x=B, y=H_total/2, ax=B+(1.5 + abs(val_l)/40.0), ay=H_total/2, text=f"<b>{val_l:.1f}</b>", showarrow=True, arrowhead=2, arrowcolor="#EA580C")
    
    # วาดแรงลมยกหลังคา (Roof Uplift)
    val_r = p_roof_ext if view_mode == "External" else (net_roof_case1 if view_mode == "Case 1" else net_roof_case2)
    fig.add_annotation(x=B/2, y=H_total + (1.5 + abs(val_r)/40.0), ax=B/2, ay=H_total, text=f"<b>Roof: {val_r:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#EF4444")
    
    fig.update_layout(title="<b>1. ด้านข้างตัดขวาง (Cross Section: หน่วย kgf/m²)</b>", xaxis_title="ความกว้างอาคาร B (ม.)", yaxis_title="ความสูง z (ม.)", xaxis_range=[-6, B+6], yaxis_range=[-1, H_total+4], height=400, plot_bgcolor="white")
    return fig

def plot_trib_area_elevation(floors, length_dim, side_type="Front"):
    fig = go.Figure()
    for f in floors:
        area_val = f['trib_area_front'] if side_type == "Front" else f['trib_area_side']
        fig.add_trace(go.Scatter(
            x=[0, length_dim, length_dim, 0, 0], y=[f['z_bottom'], f['z_bottom'], f['z_top'], f['z_top'], f['z_bottom']],
            fill="toself", name=f"ชั้น {f['floor_num']}",
            text=f"<b>ชั้น {f['floor_num']}</b><br>ระดับสูง: {f['z_bottom']:.1f} ถึง {f['z_top']:.1f} ม.<br>พื้นที่รับแรง: {area_val:.1f} m²", hoverinfo="text"
        ))
        fig.add_annotation(x=length_dim/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor_num']}: Area = {area_val:.1f} m²</b><br>(กว้าง {length_dim}ม. × สูง {f['height']}ม.)", showarrow=False, font=dict(color="white", size=10))
    
    title_text = f"<b>2. พื้นที่รับแรงหน้าตรงผนังรับลม (Front View: L = {length_dim} ม.)</b>" if side_type == "Front" else f"<b>3. พื้นที่รับแรงผนังด้านข้าง (Side View: B = {length_dim} ม.)</b>"
    fig.update_layout(title=title_text, xaxis_title="ความยาวหน้าแผงผนัง (ม.)", yaxis_title="ระดับความสูง z (ม.)", yaxis_range=[-1, H_total+2], height=400, plot_bgcolor="white", showlegend=False)
    return fig

# ==========================================
# TABS NAVIGATION
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 ขอบเขตพื้นที่รับลม & แผนภาพแรง", "⚖️ ตรวจสอบเปรียบเทียบ Base Shear", "📑 รายการคำนวณเชิงลึก"])

# ------------------------------------------
# TAB 1: Area & Visual Diagrams
# ------------------------------------------
with tab1:
    st.markdown("#### 📐 แผนภาพอธิบายการแปลงหน่วยแรงดันแผ่ ($kgf/m^2$) ร่วมกับพื้นที่รับแรง ($m^2$)")
    st.info("💡 **คำอธิบายสัจพจน์ทางวิศวกรรม:** หน่วย `kgf/m²` คือแรงดันที่กระจายตัวสม่ำเสมอเต็มหน้าผาบ้าน แต่เสาและคานจะรับแรงรวมได้ก็ต่อเมื่อนำแรงดันนี้ไป **'คูณกับเนื้อที่กรอบสี่เหลี่ยมรับลมของชั้นนั้นๆ (Tributary Area)'** ดังรูปภาพด้านขวา แรงดันจึงจะเปลี่ยนสภาพเป็นแรงลัพธ์แบบจุดสถิตรวมเป็นหน่วยกิโลนิวตัน (`kN`) วิ่งเข้าสู่ศูนย์กลางชั้นอาคาร")
    
    view_option = st.radio("เลือกโหลดพิจารณาบนรูปตัดอาคาร:", ["External", "Case 1", "Case 2"], horizontal=True)
    
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(plot_cross_section_full(floors_data, view_option), use_container_width=True)
    with c2: st.plotly_chart(plot_trib_area_elevation(floors_data, L, "Front"), use_container_width=True)
    
    st.markdown("---")
    st.markdown("##### 🧱 มิติด้านข้างอาคาร (สำหรับออกแบบระบบแผ่น Cladding / โครงเคร่วและกระจกข้างอาคาร)")
    st.plotly_chart(plot_trib_area_elevation(floors_data, B, "Side"), use_container_width=True)

# ------------------------------------------
# TAB 2: Base Shear Comparison
# ------------------------------------------
with tab2:
    st.markdown("#### ⚖️ การตรวจสอบและเปรียบเทียบแรงเฉือนที่ฐานอาคารรวม (Base Shear Comparison)")
    st.markdown(f"**ℹ️ ที่มาของแรงแผ่นดินไหว ($V_{{EQ}}$):** {eq_source_text}")
    
    governing_force = "WIND LOAD (แรงลมสถิตสุทธิ)" if V_wind_max > V_EQ_calculated else "EARTHQUAKE LOAD (แรงแผ่นดินไหว)"
    color_box = "#FEE2E2" if V_wind_max > V_EQ_calculated else "#E0F2FE"
    border_color = "#EF4444" if V_wind_max > V_EQ_calculated else "#0284C7"
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["แรงลม Case 1 (+Internal Suction)", "แรงลม Case 2 (+Internal Pressure)", "แรงแผ่นดินไหว (V_EQ)"],
        y=[V_wind_case1, V_wind_case2, V_EQ_calculated],
        marker_color=["#2563EB", "#1D4ED8", "#EF4444"],
        text=[f"{V_wind_case1:.1f} kN", f"{V_wind_case2:.1f} kN", f"{V_EQ_calculated:.1f} kN"], textposition='auto'
    ))
    fig_bar.update_layout(title="<b>เปรียบเทียบแรงเฉือนรวมที่ฐานอาคาร (Total Base Shear Comparison)</b>", yaxis_title="Base Shear (kN)", height=350, plot_bgcolor="white")
    
    b_col1, b_col2 = st.columns([3, 2])
    with b_col1: st.plotly_chart(fig_bar, use_container_width=True)
    with b_col2:
        st.markdown(f"""
        <div class="verdict-box" style="background-color: {color_box}; border-left: 6px solid {border_color}; margin-bottom:15px;">
            📋 ผลลัพธ์ตัดสินระบบแรงด้านข้างควบคุม (Governing Load):<br>
            <span style="font-size: 1.3rem; color: {border_color};">{governing_force} เป็นตัวควบคุมหลัก!</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        * **แรงลมสูงสุดรวม ($V_{{Wind, max}}$):** `{V_wind_max:.2f}` kN
        * **แรงแผ่นดินไหวร่วมตรวจสอบ ($V_{{EQ}}$):** `{V_EQ_calculated:.2f}` kN
        * อัตราส่วนสัดส่วนแรงจากภัยพิบัติ $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / (V_EQ_calculated if V_EQ_calculated > 0 else 1):.2f}`** เท่า
        """)
        if V_wind_max > V_EQ_calculated:
            st.success("🎯 **ข้อเสนอแนะทางวิศวกรรม:** แรงลมเป็นแรงหลักที่ส่งผลต่อเสาและคานในการต้านแรงด้านข้าง แต่อย่าลืมตรวจสอบรายละเอียดเหล็กปลอกต้านทานแผ่นดินไหวขั้นต่ำตามข้อกำหนดกฎหมายด้วยครับ")
        else:
            st.warning("🎯 **ข้อเสนอแนะทางวิศวกรรม:** แรงแผ่นดินไหวมีอิทธิพลเหนือกว่าอย่างเห็นได้ชัด! โครงสร้างต้องได้รับการออกแบบและจัดรายละเอียดเหล็กเสริม (Ductile Detailing) ให้มีความเหนียวตามมาตรฐาน มยผ. 1301/1302")

# ------------------------------------------
# TAB 3: Advanced Calculation Report
# ------------------------------------------
with tab3:
    st.markdown("#### 📑 ตารางสรุปหน่วยแรงดัน พื้นที่รับลม และแรงลัพธ์รายชั้นแบบมืออาชีพ")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "ขอบเขตความสูง (ม.)": f"{f['z_bottom']:.1f} ถึง {f['z_top']:.1f}",
            "พื้นที่รับลมหน้าตรง A_front (m²)": round(f['trib_area_front'], 1),
            "พื้นที่รับลมด้านข้าง A_side (m²)": round(f['trib_area_side'], 1),
            "Net Windward C1 (kgf/m²)": round(f['net_w_case1'], 1),
            "Net Sidewall C1 (kgf/m²)": round(f['net_s_case1'], 1),
            "🔥 Story Force C1 (kN)": round(f['f_story_kn_c1'], 2),
            "Net Windward C2 (kgf/m²)": round(f['net_w_case2'], 1),
            "Net Sidewall C2 (kgf/m²)": round(f['net_s_case2'], 1),
            "🔥 Story Force C2 (kN)": round(f['f_story_kn_c2'], 2)
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    st.markdown(f"""
    ---
    ### **🧾 บันทึกและรายละเอียดการคำนวณขั้นอนุมัติแบบ (ส่งกองช่าง)**
    * **แรงดันอ้างอิงพื้นฐาน ($q$):** ความเร็วลมเลือกใช้จากกลุ่มพื้นที่ `{V_input}` m/s $\\rightarrow$ $q = 0.5 \\cdot 1.25 \\cdot V^2 / 9.80665 =$ **`{q:.2f}` kgf/m²**
    * **ระดับยอดอาคาร ($H = {H_total:.2f}$ ม.):** ค่าประกอบภูมิประเทศ $C_{{e,H}} = {Ce_H:.3f}$ $\\rightarrow$ แรงดันยอดอาคาร $q_h =$ **`{qh:.2f}` kgf/m²**
    * **แรงแผ่ที่คงที่ตลอดความสูง (หลังคาและผนังตามลม):**
      * หน่วยแรงดันลมภายนอกผนังตามลม (Leeward Exterior): $p_l =$ `{p_leeward:.2f}` kgf/m²
      * หน่วยแรงดันลมภายนอกหลังคา (Roof Uplift Exterior): $p_{{roof}} =$ `{p_roof_ext:.2f}` kgf/m²
      * แรงดันลมภายในอาคาร (Internal Pressure): $p_{{int+}} =$ `{p_internal_pos:.2f}` kgf/m² | $p_{{int-}} =$ `{p_internal_neg:.2f}` kgf/m²
    """)
    
    # พิมพ์รายละเอียดสูตรถอดตัวเลขทีละชั้น
    st.markdown("### 🧮 สมการกระจายแรงและการรวมแรงลัพธ์รายชั้นอย่างละเอียด:")
    for f in floors_data:
        with st.expander(f"⚙️ คลิกดูขั้นตอนคำนวณของ: ชั้นที่ {f['floor_num']} (ระดับ $z_{{mid}} = {f['z_mid']:.2f}$ ม.)", expanded=False):
            st.markdown(f"""
            * **ค่าปรับแก้ระดับความสูงเฉพาะชั้น:** $C_e = {f['Ce']:.3f}$ (ที่มา: {f['Ce_exp']})
            * **แรงดันภายนอกเฉพาะจุด:** ผนังหน้าตรง $p_w = {f['p_windward']:.2f}$ kgf/m² | ผนังด้านข้าง $p_s = {f['p_sidewall_ext']:.2f}$ kgf/m²
            
            **📍 กรณีที่ 1 (+ แรงดูดภายในอาคาร $p_{{int-}} = {p_internal_neg:.2f}$ kgf/m²):**
            * หน่วยแรงดันสุทธิผนังรับลม: $p_{{net, windward}} = {f['p_windward']:.2f} - ({p_internal_neg:.2f}) =$ **`{f['net_w_case1']:.2f}` kgf/m²**
            * หน่วยแรงดันสุทธิผนังตามลม: $p_{{net, leeward}} = {p_leeward:.2f} - ({p_internal_neg:.2f}) =$ **`{net_l_case1:.2f}` kgf/m²**
            * หน่วยแรงดันสุทธิผนังด้านข้าง: $p_{{net, sidewall}} = {f['p_sidewall_ext']:.2f} - ({p_internal_neg:.2f}) =$ **`{f['net_s_case1']:.2f}` kgf/m²**
            * **แปลงเป็น Story Force ลัพธ์ประจำชั้น (Case 1):**
              $$F_{{story}} = (p_{{net, w}} + |p_{{net, l}}|) \\times A_{{front}} \\times 0.00980665$$
              $$F_{{story}} = ({f['net_w_case1']:.2f} + |{net_l_case1:.2f}|) \\times {f['trib_area_front']:.1f} \\times 0.00980665 = \\mathbf{{{f['f_story_kn_c1']:.2f} \\text{{ kN}}}}$$
              
            **📍 กรณีที่ 2 (+ แรงดันภายในอาคาร $p_{{int+}} = {p_internal_pos:.2f}$ kgf/m²):**
            * หน่วยแรงดันสุทธิผนังรับลม: $p_{{net, windward}} = {f['p_windward']:.2f} - ({p_internal_pos:.2f}) =$ **`{f['net_w_case2']:.2f}` kgf/m²**
            * หน่วยแรงดันสุทธิผนังด้านข้าง: $p_{{net, sidewall}} = {f['p_sidewall_ext']:.2f} - ({p_internal_pos:.2f}) =$ **`{f['net_s_case2']:.2f}` kgf/m²**
            * **แปลงเป็น Story Force ลัพธ์ประจำชั้น (Case 2):**
              $$F_{{story}} = (p_{{net, w}} + |p_{{net, l}}|) \\times A_{{front}} \\times 0.00980665 = \\mathbf{{{f['f_story_kn_c2']:.2f} \\text{{ kN}}}}$$
            """)

    # ปุ่มดาวน์โหลด
    csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(label="📥 ดาวน์โหลดสรุปตารางหน่วยแรงและพื้นที่รับลม (.csv)", data=csv_data, file_name="Comprehensive_Wind_Seismic_Report.csv", mime="text/csv")
