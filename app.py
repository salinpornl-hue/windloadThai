import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math (มยผ. 1311-50 / มยผ. 1302)
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q (kgf/m²)"""
    rho = 1.25  
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665  

def get_Ce_details(z, exposure):
    """คำนวณ Ce อิงตามประเภทภูมิประเทศพร้อมส่งคำอธิบายสูตร"""
    z_eff = max(z, 6.0) 
    if 'A' in exposure:
        alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure:
        alpha, min_val, max_val = 0.28, 0.7, 1.2
    else:
        alpha, min_val, max_val = 0.40, 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"(z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ใช้ค่าควบคุม {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจาก z = {z} ม. ต่ำกว่าขั้นต่ำ (6.0 ม.) จึงปรับใช้ z_eff = 6.0 ม. | " + explanation
    return ce, explanation

# ==========================================
# Streamlit UI Setup & Custom CSS Styling
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro", layout="wide")

# ปรับแต่งธีมหน้าตาด้วย CSS ของ Streamlit ให้ดูพรีเมียมและสะอาดตา
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.05rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.35rem; font-weight: 700; color: #1E3A8A; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .card-stat { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer (มยผ. 1311-50 / 1302)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิรายชั้น, พื้นที่รับแรงควบคุม (Tributary Area) และตรวจสอบเปรียบเทียบแรงเฉือนฐานรากอาคาร</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR CONTROL PANEL (ย้ายส่วนควบคุมไปไว้ด้านข้างทั้งหมด)
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=50)
st.sidebar.markdown("### ⚙️ ข้อกำหนดด้านวิศวกรรม")

st.sidebar.subheader("1. ข้อมูลแรงลมพื้นฐาน")
V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง)', 'C (ในเมืองใหญ่/ตึกสูง)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. ข้อกำหนดแรงแผ่นดินไหว")
eq_mode = st.sidebar.radio("วิธีการคำนวณแรงแผ่นดินไหว (V_EQ):", ["ให้โปรแกรมประมาณการสถิตเทียบเท่า", "ระบุค่าแรงเฉือนฐานเองโดยตรง (kN)"])

if eq_mode == "ให้โปรแกรมประมาณการสถิตเทียบเท่า":
    w_dl_ll = st.sidebar.number_input("น้ำหนักตึกรวมเฉลี่ยรายชั้น (kgf/m²)", value=600.0, step=50.0, help="รวมน้ำหนักบรรทุกคงที่ + น้ำหนักบรรทุกจรจรตามสัดส่วน")
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แรงแผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
else:
    V_EQ_manual = st.sidebar.number_input("ระบุค่าแรงเฉือนฐาน V_EQ (kN)", value=120.0, step=10.0, min_value=0.0)

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์รูปทรงอาคาร")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed Building)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)
Cp_s = st.sidebar.number_input("Cp ผนังด้านข้าง (Sidewall)", value=-0.7, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Flat Roof)", value=-0.7, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions & Story Configuration
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

col_b, col_l, col_n = st.columns(3)
with col_b: B = st.number_input("ความกว้างอาคารขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l: L = st.number_input("ความยาวอาคารตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n: num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", value=3, min_value=1, step=1)

with st.expander("📐 คลิกเพื่อปรับแต่งความสูงแยกแต่ละชั้นได้อย่างอิสระ", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        col_idx = i % 4
        default_h = 4.0 if i == 0 else 3.5 
        with floor_cols[col_idx]:
            h_val = st.number_input(f"ความสูงชั้นที่ {i+1} (ม.)", value=default_h, min_value=1.0, step=0.1, key=f"h_f_{i}")
            floor_heights.append(h_val)

H_total = sum(floor_heights)

# ==========================================
# Core Engine Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

# คำนวณส่วนประกอบแรงดันลมภายนอกที่คงที่ตลอดความสูงหลังคา/ผนังด้านตามลม
p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_sidewall_ext = Iw_input * qh * Cg_input * Cp_s
p_roof_ext = Iw_input * qh * Cg_input * Cp_r

p_internal_pos = qh * GCpi     
p_internal_neg = qh * (-GCpi)  

net_l_case1 = p_leeward - p_internal_neg
net_l_case2 = p_leeward - p_internal_pos
net_r_case1 = p_roof_ext - p_internal_neg
net_r_case2 = p_roof_ext - p_internal_pos

z_cumulative = 0
floors_data = []

# วนลูปคำนวณข้อมูลแยกรายชั้น (Multi-story processing)
for i in range(num_stories):
    h_current = floor_heights[i]
    z_bottom = z_cumulative
    z_top = z_cumulative + h_current
    z_mid = (z_bottom + z_top) / 2.0 
    
    Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
    p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
    
    net_w_case1 = p_w_z - p_internal_neg
    net_w_case2 = p_w_z - p_internal_pos
    
    # 🎯 คำนวณพื้นที่รับลม (Tributary Area) ประจำชั้น
    trib_area_front = L * h_current  
    
    # คำนวณแรงลัพธ์ประจำชั้น (Story Force) หน่วยเป็น kN (1 kgf = 9.80665 N -> /1000 = 0.00980665 kN)
    f_story_kn_c1 = (net_w_case1 - net_l_case1) * trib_area_front * 0.00980665
    f_story_kn_c2 = (net_w_case2 - net_l_case2) * trib_area_front * 0.00980665
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_mid_exp, "p_windward": p_w_z,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2,
        "trib_area_front": trib_area_front,
        "f_story_kn_c1": f_story_kn_c1, "f_story_kn_c2": f_story_kn_c2
    })
    z_cumulative = z_top

V_wind_case1 = sum([f['f_story_kn_c1'] for f in floors_data])
V_wind_case2 = sum([f['f_story_kn_c2'] for f in floors_data])
V_wind_max = max(V_wind_case1, V_wind_case2)

# คำนวณค่าแรงแผ่นดินไหวอ้างอิง
if eq_mode == "ให้โปรแกรมประมาณการสถิตเทียบเท่า":
    W_building_kN = (B * L) * num_stories * w_dl_ll * 0.00980665
    V_EQ_calculated = cs_coeff * W_building_kN
else:
    V_EQ_calculated = V_EQ_manual

# ==========================================
# Plotly Visualization Functions
# ==========================================
def plot_cross_section(floors, view_mode):
    fig = go.Figure()
    # วาดตัวตึกเชิงโครงสร้าง
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30, 58, 138, 0.02)", line=dict(color="#1E3A8A", width=3.5), name="โครงสร้าง"))
    
    # พล็อตเส้นแบ่งชั้นโครงสร้าง
    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="rgba(75, 85, 99, 0.3)", width=1.5, dash="dash"))
        
        # คัดเลือกหน่วยแรงดันตามโหมดโหลดที่ผู้ใช้เลือก
        val_w = f['p_windward'] if view_mode == "External" else (f['net_w_case1'] if view_mode == "Case 1" else f['net_w_case2'])
        arrow_len = 1.5 + abs(val_w) / 35.0
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_len, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y", text=f"<b>{val_w:.1f}</b>", showarrow=True, arrowhead=2, arrowsize=1.1, arrowcolor="#DC2626", font=dict(color="#DC2626", size=11))
        
    val_l = p_leeward if view_mode == "External" else (net_l_case1 if view_mode == "Case 1" else net_l_case2)
    fig.add_annotation(x=B, y=H_total/2, ax=B+(1.5 + abs(val_l)/35.0), ay=H_total/2, text=f"<b>Leeward: {val_l:.1f}</b>", showarrow=True, arrowhead=2, arrowcolor="#EA580C", font=dict(color="#EA580C"))
    
    val_r = p_roof_ext if view_mode == "External" else (net_r_case1 if view_mode == "Case 1" else net_r_case2)
    fig.add_annotation(x=B/2, y=H_total+(1.5 + abs(val_r)/35.0), ax=B/2, ay=H_total, text=f"<b>Roof Uplift: {val_r:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#9333EA", font=dict(color="#9333EA"))
    
    fig.update_layout(title="<b>1. แผนภาพหน่วยแรงดันลมบนหน้าตัดอาคาร (Cross Section: kgf/m²)</b>", xaxis_title="ความกว้างตึก B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)", xaxis_range=[-7, B+7], yaxis_range=[-1, H_total+4], height=420, margin=dict(l=20, r=20, t=50, b=20), plot_bgcolor="white")
    return fig

def plot_elevation_tributary(floors):
    fig = go.Figure()
    # กำหนดเฉดสีน้ำเงินไล่ระดับความโปร่งใสสำหรับสลับสีแต่ละชั้นอาคารให้สังเกตง่าย
    colors = ["rgba(37, 99, 235, 0.6)", "rgba(96, 165, 250, 0.5)", "rgba(147, 197, 253, 0.4)", "rgba(191, 219, 254, 0.4)"]
    
    for idx, f in enumerate(floors):
        c_fill = colors[idx % len(colors)]
        fig.add_trace(go.Scatter(
            x=[0, L, L, 0, 0], y=[f['z_bottom'], f['z_bottom'], f['z_top'], f['z_top'], f['z_bottom']],
            fill="toself", fillcolor=c_fill, line=dict(color="#2563EB", width=1.5), name=f"ชั้น {f['floor_num']}",
            text=f"<b>ชั้น {f['floor_num']}</b><br>ขอบเขตพิกัดความสูง: {f['z_bottom']:.1f} ถึง {f['z_top']:.1f} ม.<br>พื้นที่รับแรงแผ่: {f['trib_area_front']:.1f} m²", hoverinfo="text"
        ))
        fig.add_annotation(x=L/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor_num']}: Area = {f['trib_area_front']:.1f} m²</b><br>(กว้าง {L}ม. × สูงช่วงชั้น {f['height']}ม.)", showarrow=False, font=dict(color="#1E3A8A", size=11))
        
    fig.update_layout(title="<b>2. ขอบเขตพื้นที่รับลมหน้าตรง (Elevation View - ด้านรับลม L)</b>", xaxis_title="ความยาวหน้าแผงผนังรับแรง L (ม.)", yaxis_title="ระดับความสูงของอาคาร z (ม.)", height=420, margin=dict(l=20, r=20, t=50, b=20), plot_bgcolor="white", showlegend=False)
    return fig

# ==========================================
# INTERACTIVE TABS SYSTEM (จัดสัดส่วนหน้ากระดาษหลัก)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ด & แผนภาพกราฟิก", "⚖️ ตรวจสอบเปรียบเทียบ Base Shear", "📑 เล่มรายการคำนวณอย่างละเอียด"])

# ------------------------------------------
# TAB 1: Dashboard & Visualizations
# ------------------------------------------
with tab1:
    st.markdown("#### 🎯 สรุปผลลัพธ์มิติตัวแปรหลักเชิงวิศวกรรม")
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: st.markdown(f'<div class="card-stat"><p style="margin:0;color:#6B7280;font-size:0.9rem;">ความสูงตึกรวม (H_total)</p><h3 style="margin:5px 0 0 0;color:#1E3A8A;">{H_total:.2f} ม.</h3></div>', unsafe_allow_html=True)
    with m_col2: st.markdown(f'<div class="card-stat"><p style="margin:0;color:#6B7280;font-size:0.9rem;">แรงลมอ้างอิงพื้นฐาน (q)</p><h3 style="margin:5px 0 0 0;color:#1E3A8A;">{q:.2f} kgf/m²</h3></div>', unsafe_allow_html=True)
    with m_col3: st.markdown(f'<div class="card-stat"><p style="margin:0;color:#6B7280;font-size:0.9rem;">Net Windward สูงสุด</p><h3 style="margin:5px 0 0 0;color:#DC2626;">{max([f["net_w_case1"] for f in floors_data]):.1f} kgf/m²</h3></div>', unsafe_allow_html=True)
    with m_col4: st.markdown(f'<div class="card-stat"><p style="margin:0;color:#6B7280;font-size:0.9rem;">แรงเฉือนฐานลมรวม (V_Wind)</p><h3 style="margin:5px 0 0 0;color:#2563EB;">{V_wind_max:.2f} kN</h3></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    view_option = st.radio("เลือกกรณีกระแสโหลด (Load Case) เพื่อพล็อตลูกศรแรงดันจำลอง:", ["External", "Case 1", "Case 2"], captions=["แรงดันลมภายนอกเพียวๆ", "แรงลมสุทธิ: ผสมกรณีเกิดแรงดูดภายใน (-)", "แรงลมสุทธิ: ผสมกรณีเกิดแรงดันภายใน (+)"], horizontal=True)
    
    # วาดรูปแผนภาพแผงคู่ขนานกันแบบ Side-by-Side ตามภาพตัวอย่างหน้างานของคุณ
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.plotly_chart(plot_cross_section(floors_data, view_option), use_container_width=True)
    with g_col2:
        st.plotly_chart(plot_elevation_tributary(floors_data), use_container_width=True)

# ------------------------------------------
# TAB 2: Base Shear Analyzer
# ------------------------------------------
with tab2:
    st.markdown("#### ⚖️ การตรวจสอบแรงเฉือนฐานอาคารเปรียบเทียบระหว่างภัยพิบัติ (Base Shear Control)")
    
    governing_force = "WIND LOAD (แรงลมสุทธิวิกฤต ควบคุมการออกแบบโครงสร้างหลักอาคาร)" if V_wind_max > V_EQ_calculated else "EARTHQUAKE LOAD (แรงแผ่นดินไหววิกฤต ควบคุมการออกแบบต้านทานแรงดัดถอน)"
    color_box = "#FEE2E2" if V_wind_max > V_EQ_calculated else "#E0F2FE"
    border_color = "#EF4444" if V_wind_max > V_EQ_calculated else "#0284C7"
    
    # กราฟแท่งแสดงการเปรียบเทียบแรงเฉือนรวมที่ฐานฐานราก
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["แรงลมรวมสุทธิ Case 1", "แรงลมรวมสุทธิ Case 2", "แรงแผ่นดินไหวควบคุม V_EQ"],
        y=[V_wind_case1, V_wind_case2, V_EQ_calculated],
        marker_color=["#3B82F6", "#1D4ED8", "#EF4444"],
        text=[f"{V_wind_case1:.2f} kN", f"{V_wind_case2:.2f} kN", f"{V_EQ_calculated:.2f} kN"],
        textposition='auto'
    ))
    fig_bar.update_layout(title="<b>สัดส่วนแรงเฉือนฐานรวมที่กระทำต่อฐานราก (Total Base Shear Comparison: kN)</b>", yaxis_title="แรงรวมฐานอาคาร (kN)", height=350, plot_bgcolor="white", margin=dict(t=40, b=20))
    
    b_col1, b_col2 = st.columns([3, 2])
    with b_col1:
        st.plotly_chart(fig_bar, use_container_width=True)
    with b_col2:
        st.markdown(f"""
        <div class="verdict-box" style="background-color: {color_box}; border-left: 6px solid {border_color};">
            📋 ผลสรุปแรงพิจารณาต้านทานแรงด้านข้าง:<br>
            <span style="font-size: 1.15rem; color: {border_color};">{governing_force}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        **📊 รายละเอียดค่าเปรียบเทียบสัดส่วน:**
        * **แรงเฉือนรวมเนื่องจากกระแสลมสูงสุด:** `{V_wind_max:.2f}` kN
        * **แรงเฉือนรวมเนื่องจากภัยแผ่นดินไหว:** `{V_EQ_calculated:.2f}` kN
        * สัดส่วนดัชนีพิจารณาแรงทำลายล้าง $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / (V_EQ_calculated if V_EQ_calculated > 0 else 1):.2f}`** เท่า
        """)

# ------------------------------------------
# TAB 3: Detailed Calculation Book & Export Data
# ------------------------------------------
with tab3:
    st.markdown("#### 💾 ตารางสรุปหน่วยแรงและแรงรวมลัพธ์สำหรับส่งออกเพื่อป้อนซอฟต์แวร์ออกแบบ")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "ระดับความสูงพิจารณา": f"{f['z_bottom']:.1f} - {f['z_top']:.1f} ม.",
            "พื้นที่รับลมหน้าตรง A (m²)": round(f['trib_area_front'], 1),
            "Windward C1 (kgf/m²)": round(f['net_w_case1'], 1),
            "Leeward C1 (kgf/m²)": round(net_l_case1, 1),
            "🔥 Story Force C1 (kN)": round(f['f_story_kn_c1'], 2),
            "Windward C2 (kgf/m²)": round(f['net_w_case2'], 1),
            "Leeward C2 (kgf/m²)": round(net_l_case2, 1),
            "🔥 Story Force C2 (kN)": round(f['f_story_kn_c2'], 2)
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    csv_bytes = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 ดาวน์โหลดตารางข้อมูลรายงานการคำนวณโครงสร้าง (.csv)", data=csv_bytes, file_name="Integrated_Wind_Seismic_Load_Report.csv", mime="text/csv")
    
    st.markdown("---")
    st.markdown("#### 📑 เล่มรายการคำนวณเชิงคณิตศาสตร์และสูตรวิศวกรรมสเต็ปต่อสเต็ป")
    
    st.markdown(f"""
    **1. สมการตั้งต้นและการหาค่าแรงลมอ้างอิงพื้นฐาน ($q$)**
    * ความเร็วลมตามมาตรฐานพิจารณาสนาม $V = {V_input}$ m/s 
    * สภาพความหนาแน่นมวลอากาศ $\\rho = 1.25$ $kg/m^3$
    * $q = 0.5 \\times 1.25 \\times V^2 / 9.80665 =$ **`{q:.2f}` kgf/m²**
    * สภาพพื้นที่ตั้งอาคารอ้างอิงคลาส: `{exposure}` $\\rightarrow$ ตัวคูณพิจารณาประกอบรวมแรงลมกระโชก $C_g = {Cg_input}$
    
    **2. แรงลมภายนอกส่วนคงตัวประจำระดับหลังคาและความสูงรวมอาคาร ($H_{{total}} = {H_total:.2f}$ ม.)**
    * สัมประสิทธิ์ประกอบความสูงยอดตึก $C_{{e,H}} = {Ce_H:.3f}$ $\\rightarrow q_h = q \\times C_{{e,H}} = {qh:.2f}$ kgf/m²
    * **แรงด้านตามลม (Leeward Exterior Pressure):** $p_l = I_w \\times q_h \\times C_g \\times C_p = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_l}) =$ **`{p_leeward:.2f}` kgf/m²**
    * **แรงดันผนังด้านข้าง (Sidewall Pressure):** $p_s = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_s}) =$ **`{p_sidewall_ext:.2f}` kgf/m²**
    * **แรงยกแผ่นหลังคาแบน (Roof Uplift Pressure):** $p_r = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_r}) =$ **`{p_roof_ext:.2f}` kgf/m²**
    """)
    
    st.markdown("##### 🧮 การถอดสเต็ปรวมสัมประสิทธิ์แรงดันสุทธิและแรงลัพธ์ประจำชั้น:")
    for f in floors_data:
        with st.expander(f"🔍 สเต็ปสูตรคำนวณถอดค่าละเอียด: ชั้นที่ {f['floor_num']} (ระดับพิจารณากึ่งกลางช่วงชั้น z = {f['z_mid']:.2f} ม.)", expanded=False):
            st.markdown(f"""
            * **ค่าประกอบความสูงประจำช่วงระดับ:** $C_e = {f['Ce']:.3f}$ *(ที่มาสูตร: {f['Ce_exp']})*
            * **หน่วยแรงดันภายนอกด้านรับลม:** $p_w = {Iw_input} \\times {q:.2f} \\times {f['Ce']:.3f} \\times {Cg_input} \\times {Cp_w} = {f['p_windward']:.2f}$ kgf/m²
            * **หน้ากว้างแผงพื้นที่รับกระแสลมขอบเขตสี่เหลี่ยม:** $A_{{trib}} = L \\times h = {L} \\times {f['height']} =$ **`{f['trib_area_front']:.1f}` m²**
            
            **📌 ถอดสมการแปลงแรงลัพธ์ประจำชั้น Case 1 (พิจารณาผลรวมแรงดูดภายในอาคาร $p_{{int-}} = {p_internal_neg:.2f}$ kgf/m²):**
            * หน่วยแรงสุทธิรับลม: $p_{{net, w}} = {f['p_windward']:.2f} - ({p_internal_neg:.2f}) = {f['net_w_case1']:.2f}$ kgf/m²
            * หน่วยแรงสุทธิตามลม: $p_{{net, l}} = {p_leeward:.2f} - ({p_internal_neg:.2f}) = {net_l_case1:.2f}$ kgf/m²
            * สมการแรงเฉือนลัพธ์: $F_{{story}} = (p_{{net, w}} - p_{{net, l}}) \\times A_{{trib}} \\times 0.00980665$
            * แทนค่า: $F_{{story}} = ({f['net_w_case1']:.2f} - ({net_l_case1:.2f})) \\times {f['trib_area_front']:.1f} \\times 0.00980665 =$ **`{f['f_story_kn_c1']:.2f}` kN**
            
            **📌 ถอดสมการแปลงแรงลัพธ์ประจำชั้น Case 2 (พิจารณาผลรวมแรงดันภายในอาคาร $p_{{int+}} = {p_internal_pos:.2f}$ kgf/m²):**
            * หน่วยแรงสุทธิรับลม: $p_{{net, w}} = {f['p_windward']:.2f} - ({p_internal_pos:.2f}) = {f['net_w_case2']:.2f}$ kgf/m²
            * หน่วยแรงสุทธิตามลม: $p_{{net, l}} = {p_leeward:.2f} - ({p_internal_pos:.2f}) = {net_l_case2:.2f}$ kgf/m²
            * แทนค่า: $F_{{story}} = ({f['net_w_case2']:.2f} - ({net_l_case2:.2f})) \\times {f['trib_area_front']:.1f} \\times 0.00980665 =$ **`{f['f_story_kn_c2']:.2f}` kN**
            """)
