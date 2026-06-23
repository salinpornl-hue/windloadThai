import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math (มยผ. 1311-50)
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
# Streamlit UI Setup & Styling
# ==========================================
st.set_page_config(page_title="Wind Load Analyzer | มยผ. 1311-50", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind Load Analyzer & Structural Report</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">โปรแกรมวิเคราะห์แรงลมแยกรายชั้นและแรงลมสุทธิ (Net Pressure) ตามมาตรฐาน มยผ. 1311-50</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงลม")

st.sidebar.subheader("1. ข้อมูลสถานที่ตั้งอาคาร")
V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("2. สัมประสิทธิ์แรงดันและลักษณะอาคาร")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อมของอาคาร", ["อาคารปิดทึบ (Enclosed Building)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

col_b, col_l, col_n = st.columns(3)
with col_b: B = st.number_input("ความกว้างอาคารขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l: L = st.number_input("ความยาวอาคารตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n: num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", value=3, min_value=1, step=1)

with st.expander("📐 คลิกเพื่อปรับแต่งความสูงแยกแต่ละชั้น", expanded=True):
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
# Engine Core Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_internal_pos = qh * GCpi     # แรงดันบวก (พองออก)
p_internal_neg = qh * (-GCpi)  # แรงดูดลบ (แฟบเข้า)

# คำนวณ Net Leeward (เนื่องจากคงที่ตลอดความสูง)
net_l_case1 = p_leeward - p_internal_neg  # Ext(-) - Int(-)
net_l_case2 = p_leeward - p_internal_pos  # Ext(-) - Int(+)

z_cumulative = 0
floors_data = []

for i in range(num_stories):
    h_current = floor_heights[i]
    z_bottom = z_cumulative
    z_top = z_cumulative + h_current
    z_mid = (z_bottom + z_top) / 2.0 
    
    Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
    p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
    
    # คำนวณ Net Windward รายชั้น
    net_w_case1 = p_w_z - p_internal_neg
    net_w_case2 = p_w_z - p_internal_pos
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_mid_exp, "p_windward": p_w_z,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2
    })
    z_cumulative = z_top

# ==========================================
# Helper Function: วาดลูกศรและกราฟิก
# ==========================================
def plot_building_wind(floors, view_mode):
    fig = go.Figure()
    
    # วาดตัวอาคาร
    fig.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], 
        fill="toself", fillcolor="rgba(30, 58, 138, 0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"
    ))
    
    # ฟังก์ชันวาดลูกศรแบบ Smart (รู้ทิศทางเข้า-ออก)
    def add_arrow(x_wall, y_pos, val, is_windward):
        arrow_len = 1.5 + abs(val) / 30.0 
        
        if is_windward: # ฝั่งซ้าย (Windward)
            if val >= 0: # แรงอัด (+) ชี้เข้าขวา
                ax, ay, x, y = -arrow_len, y_pos, 0, y_pos
                color, text_pos = "#DC2626", "right" # แดง
            else: # แรงดูด (-) ชี้ออกซ้าย
                ax, ay, x, y = 0, y_pos, -arrow_len, y_pos
                color, text_pos = "#9333EA", "left" # ม่วง
        else: # ฝั่งขวา (Leeward)
            if val >= 0: # แรงอัด (+) ชี้เข้าซ้าย
                ax, ay, x, y = B + arrow_len, y_pos, B, y_pos
                color, text_pos = "#DC2626", "left"
            else: # แรงดูด (-) ชี้ออกขวา
                ax, ay, x, y = B, y_pos, B + arrow_len, y_pos
                color, text_pos = "#EA580C", "right" # ส้ม
                
        fig.add_annotation(x=x, y=y, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{val:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowsize=1.2, 
                           arrowcolor=color, font=dict(color=color, size=10), xanchor=text_pos)

    # วาดเส้นแบ่งชั้นและลูกศร
    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="rgba(75, 85, 99, 0.3)", width=1.5, dash="dash"))
        fig.add_annotation(x=B + 0.3, y=f['z_top'], text=f"<b>z = {f['z_top']:.2f} m</b>", showarrow=False, xanchor="left", font=dict(size=10, color="#2563EB"))
        
        # เลือกข้อมูลที่จะวาดตาม Mode
        if view_mode == "External":
            val_w = f['p_windward']
        elif view_mode == "Case 1":
            val_w = f['net_w_case1']
        else:
            val_w = f['net_w_case2']
            
        add_arrow(x_wall=0, y_pos=f['z_mid'], val=val_w, is_windward=True)

    # วาดฝั่ง Leeward
    if view_mode == "External":
        val_l = p_leeward
    elif view_mode == "Case 1":
        val_l = net_l_case1
    else:
        val_l = net_l_case2
        
    add_arrow(x_wall=B, y_pos=H_total/2, val=val_l, is_windward=False)

    title_text = "แรงลมภายนอกเท่านั้น (External Pressure)" if view_mode == "External" else f"แรงลมสุทธิ {view_mode} (Net Pressure)"
    fig.update_layout(
        title=dict(text=f"<b>แผนภาพ: {title_text}</b>", font=dict(size=14, color="#1E3A8A"), x=0.5),
        xaxis_title="ความกว้างอาคาร (เมตร)", yaxis_title="ความสูง (เมตร)", 
        yaxis_range=[-1, H_total + 2], xaxis_range=[-7, B + 7], height=500, margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white", showlegend=False
    )
    fig.update_xaxes(showgrid=True, gridcolor='#E5E7EB')
    fig.update_yaxes(showgrid=True, gridcolor='#E5E7EB')
    return fig

# ==========================================
# TABS NAVIGATION
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ด & กราฟิกจำลอง", "📑 เล่มรายการคำนวณอย่างละเอียด", "💾 ตารางสรุปโหลดออกแบบ"])

# ------------------------------------------
# TAB 1: Dashboard
# ------------------------------------------
with tab1:
    st.markdown("#### 🎯 สรุปผลลัพธ์หลักจากการคำนวณ")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: st.metric("ความสูงรวม (H)", f"{H_total:.2f} m")
    with m_col2: st.metric("แรงลมอ้างอิง (q)", f"{q:.2f} kgf/m²")
    with m_col3: st.metric("Net Windward สูงสุด", f"{floors_data[-1]['net_w_case1']:.1f} kgf/m²")
    with m_col4: st.metric("Net Leeward สูงสุด", f"{abs(net_l_case2):.1f} kgf/m² (ดูด)")

    st.markdown("---")
    st.markdown("#### 📐 เลือกแสดงแผนภาพแรงลมกระทำต่อโครงสร้าง")
    
    # ควบคุมการแสดงผลรูปภาพแบบ Interactive
    view_option = st.radio("เลือกกรณีโหลด (Load Case):", 
                           ["External", "Case 1", "Case 2"], 
                           captions=["แรงลมภายนอกเพียวๆ", "แรงลมสุทธิ: หักล้างแรงดูดภายในอาคาร (-)", "แรงลมสุทธิ: หักล้างแรงดันภายในอาคาร (+)"], 
                           horizontal=True)
    
    fig_show = plot_building_wind(floors_data, view_option)
    st.plotly_chart(fig_show, use_container_width=True)

# ------------------------------------------
# TAB 2: Calculation Report
# ------------------------------------------
with tab2:
    st.markdown("#### 📑 เล่มรายการคำนวณโครงสร้างอย่างเป็นสเต็ป (ส่งตรวจอนุมัติ)")
    st.markdown(f"""
    ### **[ส่วนที่ 1 - 3]: ตัวแปรตั้งต้น**
    * $V$ = `{V_input}` m/s, Exposure = `{exposure}`
    * $q = 0.5 \\cdot 1.25 \\cdot {V_input}^2 / 9.80665$ = **`{q:.4f}` kgf/m²**
    * $GC_{{pi}}$ = `±{GCpi:.2f}`, $C_p \\text{{(Windward)}}$ = `{Cp_w:.2f}`, $C_p \\text{{(Leeward)}}$ = `{Cp_l:.2f}`
    
    ---
    ### **[ส่วนที่ 4]: แรงลมภายนอกด้านรับลม (Windward) แยกรายชั้น**
    สมการ: $p_{{w}} = I_w \\cdot q \\cdot C_e \\cdot C_g \\cdot C_p$
    """)
    for f in floors_data:
        st.markdown(f"- **ชั้น {f['floor_num']} ($z = {f['z_mid']:.2f}$ ม.):** $C_e = {f['Ce']:.3f}$ $\\rightarrow$ $p_w = {Iw_input} \\cdot {q:.2f} \\cdot {f['Ce']:.3f} \\cdot {Cg_input} \\cdot {Cp_w} =$ **`{f['p_windward']:.2f}` kgf/m²**")

    st.markdown(f"""
    ---
    ### **[ส่วนที่ 5]: แรงลมภายนอกด้านตามลม (Leeward) และแรงลมภายใน**
    * $C_e$ ที่ยอดอาคาร ($H = {H_total:.2f}$ ม.) = `{Ce_H:.3f}` $\\rightarrow$ $q_h = {qh:.2f}$ kgf/m²
    * **Leeward ($p_l$):** $p_l = {Iw_input} \\cdot {qh:.2f} \\cdot {Cg_input} \\cdot ({Cp_l}) =$ **`{p_leeward:.2f}` kgf/m²** *(แรงดูดภายนอก)*
    * **Internal (+):** $p_{{int+}} = {qh:.2f} \\cdot (+{GCpi}) =$ **`{p_internal_pos:.2f}` kgf/m²**
    * **Internal (-):** $p_{{int-}} = {qh:.2f} \\cdot (-{GCpi}) =$ **`{p_internal_neg:.2f}` kgf/m²**
    
    ---
    ### **[ส่วนที่ 6]: การคำนวณหน่วยแรงลมสุทธิ (Net Pressure)**
    สมการออกแบบหลัก: $$p_{{net}} = p_{{ext}} - p_{{int}}$$
    *(หมายเหตุ: ค่า + คือแรงอัดเข้าหาผิวผนัง, ค่า - คือแรงดูดออกจากผิวผนัง)*
    """)
    
    for f in floors_data:
        with st.expander(f"🧮 แสดงการถอดสมการแรงลมสุทธิของ: ชั้นที่ {f['floor_num']}", expanded=False):
            st.markdown(f"""
            **กรณีที่ 1: ผสมแรงดูดภายในอาคาร ($p_{{int-}}$)**
            * **ผนังรับลม (Windward):** $p_{{net}} = {f['p_windward']:.2f} - ({p_internal_neg:.2f}) =$ **`{f['net_w_case1']:.2f}` kgf/m²**
            * **ผนังตามลม (Leeward):** $p_{{net}} = {p_leeward:.2f} - ({p_internal_neg:.2f}) =$ **`{net_l_case1:.2f}` kgf/m²**
            
            **กรณีที่ 2: ผสมแรงดันภายในอาคาร ($p_{{int+}}$)**
            * **ผนังรับลม (Windward):** $p_{{net}} = {f['p_windward']:.2f} - ({p_internal_pos:.2f}) =$ **`{f['net_w_case2']:.2f}` kgf/m²**
            * **ผนังตามลม (Leeward):** $p_{{net}} = {p_leeward:.2f} - ({p_internal_pos:.2f}) =$ **`{net_l_case2:.2f}` kgf/m²**
            """)

# ------------------------------------------
# TAB 3: Design Output & Export
# ------------------------------------------
with tab3:
    st.markdown("#### 💾 ตารางสรุปหน่วยแรงลมสุทธิสำหรับป้อนโปรแกรมออกแบบโครงสร้าง")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "Ext. Windward": round(f['p_windward'], 2),
            "Net Windward (Case 1)": round(f['net_w_case1'], 2),
            "Net Windward (Case 2)": round(f['net_w_case2'], 2),
            "Ext. Leeward": round(p_leeward, 2),
            "Net Leeward (Case 1)": round(net_l_case1, 2),
            "Net Leeward (Case 2)": round(net_l_case2, 2)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 ดาวน์โหลดตาราง CSV", data=csv_data, file_name="WindLoad_NetPressure.csv", mime="text/csv")
