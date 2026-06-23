import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# ฟังก์ชันคำนวณตามมาตรฐาน
# ==========================================
def calculate_velocity_pressure(V):
    """คำนวณหน่วยแรงลมอ้างอิง (q) ในหน่วย kgf/m^2"""
    rho = 1.25 # kg/m^3
    return (0.5 * rho * (V ** 2)) / 9.80665

def get_Ce(z, exposure):
    """
    ประมาณค่าประกอบการเปิดโล่ง (Ce) ตามความสูงและสภาพภูมิประเทศ
    (หมายเหตุ: ใช้สมการจำลองเพื่อการแสดงผล ควรปรับจูนตามตาราง มยผ. 1311-50 อีกครั้ง)
    """
    z = max(z, 6.0) # มักจะคงที่ที่ความสูงต่ำกว่า 6-10 เมตร
    if exposure == 'A (โล่ง/ชายฝั่ง)':
        return min(max((z / 10.0) ** 0.20, 0.9), 1.5)
    elif exposure == 'B (ชานเมือง)':
        return min(max((z / 10.0) ** 0.28, 0.7), 1.2)
    else: # C (เมือง/ตึกสูงหนาแน่น)
        return min(max((z / 10.0) ** 0.40, 0.5), 1.0)

# ==========================================
# Streamlit UI
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50", layout="wide")

st.title("🌪️ โปรแกรมคำนวณหน่วยแรงลมออกแบบ (ขั้นสูง)")
st.caption("อ้างอิงมาตรฐาน มยผ. 1311-50 สำหรับอาคารแข็งเกร็ง (Rigid Building)")
st.markdown("---")

# แบ่งหน้าจอรับข้อมูลเป็น 3 คอลัมน์
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📍 1. ข้อมูลสถานที่")
    zone_dict = {
        "โซน 1 (25 m/s)": 25.0,
        "โซน 2 (27 m/s)": 27.0,
        "โซน 3 (29 m/s)": 29.0,
        "โซน 4 (38 m/s) - พายุไต้ฝุ่น": 38.0
    }
    zone_select = st.selectbox("เลือกโซนความเร็วลมพื้นฐาน (V)", list(zone_dict.keys()))
    V_input = zone_dict[zone_select]
    
    exposure = st.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง)', 'C (เมือง/ตึกสูง)'])

with col2:
    st.subheader("🏢 2. ข้อมูลอาคาร")
    h_total = st.number_input("ความสูงรวมของอาคาร (m)", min_value=3.0, value=20.0, step=1.0)
    step_z = st.number_input("ระยะห่างแต่ละชั้นที่ต้องการคำนวณ (m)", min_value=1.0, value=3.0, step=1.0)
    
    importance_dict = {"อาคารทั่วไป (1.0)": 1.0, "อาคารสำคัญ (1.15)": 1.15}
    Iw_input = importance_dict[st.selectbox("ประเภทความสำคัญอาคาร (Iw)", list(importance_dict.keys()))]

with col3:
    st.subheader("🌬️ 3. สัมประสิทธิ์ประกอบ")
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1, help="อาคารแข็งเกร็ง = 2.0")
    Cp_windward = st.number_input("Cp ด้านรับลม (Windward)", value=0.8, step=0.1)
    Cp_leeward = st.number_input("Cp ด้านตามลม (Leeward)", value=-0.5, step=0.1, help="ค่าเป็นลบหมายถึงแรงดูดออก")

st.markdown("---")

# ==========================================
# การคำนวณและสร้างตาราง
# ==========================================
if st.button("🚀 ประมวลผลการคำนวณ (Generate Profile)", use_container_width=True):
    
    q = calculate_velocity_pressure(V_input)
    st.success(f"หน่วยแรงลมอ้างอิง (q) = **{q:.2f} kgf/m²**")
    
    # สร้าง List ของความสูง (z) ตั้งแต่ 0 ถึง h_total
    heights = np.arange(0, h_total + step_z, step_z)
    if heights[-1] != h_total: 
        heights = np.append(heights, h_total) # เก็บเศษความสูงชั้นบนสุด
        
    results = []
    
    for z in heights:
        if z == 0: continue # ข้ามที่ระดับดิน
        
        Ce = get_Ce(z, exposure)
        
        # p = Iw * q * Ce * Cg * Cp
        p_windward = Iw_input * q * Ce * Cg_input * Cp_windward
        
        # Leeward ปกติคิดที่ความสูงครึ่งหนึ่งของอาคาร หรือคงที่ตลอดความสูงตาม มยผ.
        # ในที่นี้สมมติให้แปรผันตามความสูงเพื่อให้เห็นความแตกต่าง หรือจะใช้ Ce ที่ระดับ h คงที่ก็ได้
        p_leeward = Iw_input * q * get_Ce(h_total, exposure) * Cg_input * Cp_leeward
        
        p_total = p_windward + abs(p_leeward) # รวมแรงเข้าและแรงดูดออก
        
        results.append({
            "ความสูง z (m)": round(z, 2),
            "Ce": round(Ce, 3),
            "Windward (kgf/m²)": round(p_windward, 2),
            "Leeward (kgf/m²)": round(p_leeward, 2),
            "แรงลมรวมที่ต้องออกแบบ (kgf/m²)": round(p_total, 2)
        })
        
    df = pd.DataFrame(results)
    
    # แสดงผล
    res_col1, res_col2 = st.columns([1.5, 2])
    
    with res_col1:
        st.markdown("### 📊 ตารางหน่วยแรงลมออกแบบ")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with res_col2:
        st.markdown("### 📈 กราฟการกระจายแรงลมตามความสูง (Wind Profile)")
        # จัด Dataframe ให้เหมาะกับการทำ Line Chart
        chart_df = df.set_index("ความสูง z (m)")[["Windward (kgf/m²)", "แรงลมรวมที่ต้องออกแบบ (kgf/m²)"]]
        st.line_chart(chart_df)
