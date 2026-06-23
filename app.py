import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q = 0.5 * rho * V^2"""
    rho = 1.25 # ความหนาแน่นอากาศ
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665 # แปลงเป็น kgf/m^2

def get_Ce(z, exposure):
    """คำนวณ Ce อิงตาม Power Law"""
    z = max(z, 6.0)
    if 'A' in exposure: return min(max((z/10.0)**0.20, 0.9), 1.5)
    elif 'B' in exposure: return min(max((z/10.0)**0.28, 0.7), 1.2)
    else: return min(max((z/10.0)**0.40, 0.5), 1.0)

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50", layout="wide")
st.title("🌪️ โปรแกรมคำนวณแรงลมออกแบบ (มยผ. 1311-50)")
st.markdown("---")

# --- รับค่าตัวแปร ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📍 1. ข้อมูลสถานที่")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
    exposure = st.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง)', 'C (เมือง/ตึกสูง)'])
    Iw_input = st.selectbox("ค่าประกอบความสำคัญ (Iw)", [1.0, 1.15])

with col2:
    st.markdown("### 🏢 2. มิติอาคาร")
    B = st.number_input("ความกว้างอาคารด้านขนานลม B (m)", value=15.0)
    L = st.number_input("ความยาวอาคารตั้งฉากลม L (m)", value=20.0)
    H = st.number_input("ความสูงชายคา H (m)", value=12.0)
    roof_angle = st.number_input("ความชันหลังคา (องศา)", value=15.0, help="0 = หลังคาแบน")

with col3:
    st.markdown("### 🌬️ 3. สภาพแวดล้อมอาคาร")
    enclosure = st.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0)
    # สมมติค่า Cp เบื้องต้น (ในการใช้งานจริงต้องเปิดตาราง L/B)
    Cp_w = st.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8)
    Cp_l = st.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5)

# ตั้งค่า GCpi ตามประเภทอาคาร
GCpi = 0.55 if "Partially" in enclosure else 0.18

st.markdown("---")

if st.button("🚀 ประมวลผลและสร้างรายการคำนวณ", use_container_width=True):
    
    # คำนวณค่าพื้นฐาน
    q = calculate_q(V_input)
    Ce_H = get_Ce(H, exposure)
    roof_height = (B/2) * np.tan(np.radians(roof_angle)) if roof_angle > 0 else 0
    H_total = H + roof_height
    
    # คำนวณแรงลมที่ความสูงหลังคา (สำหรับ Leeward และ Internal)
    qh = q * Ce_H
    
    # คำนวณแรงลมอ้างอิงบนผนัง
    p_windward = Iw_input * q * Ce_H * Cg_input * Cp_w
    p_leeward = Iw_input * qh * Cg_input * Cp_l # ใช้ qh ที่ความสูงยอด
    p_internal_pos = qh * GCpi
    p_internal_neg = qh * (-GCpi)
    
    # ----------------------------------------
    # 1. แสดงรูปภาพประกอบอาคาร (Plotly)
    # ----------------------------------------
    st.subheader("📐 แผนภาพแรงลมจำลอง (Wind Pressure Schematic)")
    
    fig = go.Figure()
    # วาดรูปร่างอาคาร 2D
    fig.add_trace(go.Scatter(
        x=[0, B, B, B/2, 0, 0], 
        y=[0, 0, H, H_total, H, 0], 
        fill="toself", fillcolor="rgba(100, 150, 250, 0.2)",
        line=dict(color="blue", width=2), name="อาคาร"
    ))
    
    # วาดลูกศร Windward
    fig.add_annotation(x=-2, y=H/2, ax=-6, ay=H/2, xref="x", yref="y", axref="x", ayref="y",
                       text="Windward", showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="red")
    
    # วาดลูกศร Leeward
    fig.add_annotation(x=B+6, y=H/2, ax=B+2, ay=H/2, xref="x", yref="y", axref="x", ayref="y",
                       text="Leeward", showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="orange")
    
    # วาดลูกศร หลังคา
    if roof_angle > 0:
        fig.add_annotation(x=B/4, y=H+(roof_height/2)+2, ax=B/4, ay=H+(roof_height/2)+5, 
                           text="Roof Wind", showarrow=True, arrowhead=2, arrowcolor="purple")
                           
    fig.update_layout(xaxis_title="ความกว้าง B (m)", yaxis_title="ความสูง (m)", 
                      yaxis_range=[0, H_total+5], xaxis_range=[-10, B+10], height=400)
    st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------
    # 2. รายการคำนวณ (Calculation Report)
    # ----------------------------------------
    st.subheader("📑 รายการคำนวณ (Calculation Report)")
    
    report = f"""
    **โครงการ:** คำนวณหน่วยแรงลมออกแบบระบบโครงสร้างหลัก (MWFRS) ตาม มยผ. 1311-50
    **ลักษณะอาคาร:** {enclosure}, รูปทรงสี่เหลี่ยม, กว้าง {B} ม., ยาว {L} ม., สูงถึงชายคา {H} ม., ความชันหลังคา {roof_angle}°
    
    **1. ตัวแปรพื้นฐานและการคำนวณหน่วยแรงลมอ้างอิง ($q$)**
    * ความเร็วลมพื้นฐาน ($V$) = **{V_input} m/s**
    * ความหนาแน่นอากาศ ($\rho$) = 1.25 $kg/m^3$
    * $q = \\frac{{0.5 \cdot \rho \cdot V^2}}{{9.80665}}$ = **{q:.2f} $kgf/m^2$**
    
    **2. สัมประสิทธิ์ประกอบการออกแบบ**
    * ค่าประกอบความสำคัญ ($I_w$) = **{Iw_input}**
    * สภาพภูมิประเทศ = **{exposure}**
    * ค่าประกอบการเปิดโล่งที่ยอดอาคาร ($C_e$) = **{Ce_H:.3f}** (คำนวณที่ความสูง {H} ม.)
    * ค่าประกอบลมกระโชก ($C_g$) = **{Cg_input}**
    * สัมประสิทธิ์แรงดันภายใน ($GC_{{pi}}$) = **$\pm${GCpi}**
    
    **3. การคำนวณหน่วยแรงลมภายนอก (External Wind Pressure: $p_{{ext}}$)**
    *สมการ:* $p_{{ext}} = I_w \cdot q \cdot C_e \cdot C_g \cdot C_p$
    * **ผนังด้านรับลม (Windward):**
      $p_{{w}} = {Iw_input} \cdot {q:.2f} \cdot {Ce_H:.3f} \cdot {Cg_input} \cdot ({Cp_w})$ = **{p_windward:.2f} $kgf/m^2$**
    * **ผนังด้านตามลม (Leeward):**
      $p_{{l}} = {Iw_input} \cdot {q:.2f} \cdot {Ce_H:.3f} \cdot {Cg_input} \cdot ({Cp_l})$ = **{p_leeward:.2f} $kgf/m^2$** *(ค่าลบคือแรงดูดออก)*
      
    **4. การคำนวณหน่วยแรงลมภายใน (Internal Wind Pressure: $p_{{int}}$)**
    *สมการ:* $p_{{int}} = q_h \cdot GC_{{pi}}$
    * แรงดันบวก: $p_{{int+}} = {qh:.2f} \cdot {GCpi}$ = **{p_internal_pos:.2f} $kgf/m^2$**
    * แรงดูดลบ: $p_{{int-}} = {qh:.2f} \cdot (-{GCpi})$ = **{p_internal_neg:.2f} $kgf/m^2$**
    
    **5. สรุปหน่วยแรงลมออกแบบสุทธิ (Net Design Pressure)**
    *หน่วยแรงลมสุทธิ = $p_{{ext}} - p_{{int}}$ (ต้องพิจารณากรณีวิกฤตที่สุด)*
    * **ผนังด้านรับลม สูงสุด (ดันเข้า):** {p_windward:.2f} - ({p_internal_neg:.2f}) = **{(p_windward - p_internal_neg):.2f} $kgf/m^2$**
    * **ผนังด้านตามลม สูงสุด (ดูดออก):** {p_leeward:.2f} - ({p_internal_pos:.2f}) = **{(p_leeward - p_internal_pos):.2f} $kgf/m^2$**
    """
    
    st.info("💡 รายการคำนวณนี้แสดงขั้นตอนอย่างเป็นระบบ คุณสามารถคัดลอก (Copy) ข้อความด้านล่างไปใส่ในเอกสารรายการคำนวณของคุณได้เลย")
    st.markdown(report)
