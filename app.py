import streamlit as st

def calculate_velocity_pressure(V):
    """คำนวณหน่วยแรงลมอ้างอิง (q) ในหน่วย kgf/m^2"""
    rho = 1.25 # kg/m^3 (ความหนาแน่นอากาศมาตรฐาน)
    q_pa = 0.5 * rho * (V ** 2) 
    q_kgf = q_pa / 9.80665 
    return q_kgf

def calculate_design_wind_pressure(V, Iw, Ce, Cg, Cp):
    """คำนวณหน่วยแรงลมออกแบบ (p) ตาม มยผ. 1311-50"""
    q = calculate_velocity_pressure(V)
    p = Iw * q * Ce * Cg * Cp
    return p, q

# ==========================================
# ส่วนหน้าตา Web Application (Streamlit UI)
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50", layout="centered")

st.title("🌪️ โปรแกรมคำนวณแรงลมออกแบบ")
st.subheader("อ้างอิงมาตรฐาน มยผ. 1311-50")
st.markdown("---")

# แบ่งหน้าจอเป็น 2 คอลัมน์สำหรับรับค่า Input
col1, col2 = st.columns(2)

with col1:
    st.markdown("**1. ข้อมูลพื้นฐาน**")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", min_value=0.0, value=25.0, step=1.0)
    Iw_input = st.selectbox("ค่าประกอบความสำคัญของอาคาร (Iw)", [1.0, 1.15], index=0, help="1.0 อาคารทั่วไป, 1.15 อาคารสำคัญ/โรงพยาบาล")

with col2:
    st.markdown("**2. สัมประสิทธิ์ประกอบ**")
    Ce_input = st.number_input("ค่าประกอบการเปิดโล่ง (Ce)", min_value=0.0, value=0.9, step=0.1)
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", min_value=0.0, value=2.0, step=0.1, help="อาคารแข็งเกร็งมักใช้ 2.0")
    Cp_input = st.number_input("สัมประสิทธิ์แรงลมภายนอก (Cp)", value=0.8, step=0.1, help="ด้านรับลม (Windward) ปกติประมาณ 0.8")

st.markdown("---")

# ปุ่มกดคำนวณ
if st.button("🚀 คำนวณหน่วยแรงลม", use_container_width=True):
    design_pressure, ref_pressure = calculate_design_wind_pressure(
        V_input, Iw_input, Ce_input, Cg_input, Cp_input
    )
    
    # แสดงผลลัพธ์แบบกล่อง Metric สวยๆ
    st.success("คำนวณสำเร็จ!")
    
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.metric(label="หน่วยแรงลมอ้างอิง (q)", value=f"{ref_pressure:.2f} kgf/m²")
    with res_col2:
        st.metric(label="หน่วยแรงลมออกแบบ (p)", value=f"{design_pressure:.2f} kgf/m²")
        
    st.info("💡 หมายเหตุ: นี่เป็นการคำนวณเบื้องต้นที่ผนังด้านเดียว ควรคำนวณทั้งด้าน Windward และ Leeward ประกอบกัน")
