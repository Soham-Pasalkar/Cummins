import streamlit as st

st.title("This is Title")
st.header("This is Header")
st.subheader("This is SubHeader")


st.markdown("This is **Markdown**. [Visit Streamlit](https://streamlit.io)")
st.text("This is Plain Text")
st.write("'st.write()' can handle mixed content like **Bold**, _Italic_ and Numbers:",123)


st.markdown("### Code Block Example ")
st.code("""st.header("1. Upload Measurement Data")
uploaded_file = st.file_uploader(
    "Upload CSV file (must contain 'time' and 'value' columns)",
    type=["csv"]
)
if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    st.subheader("Raw Data Preview")
    st.dataframe(data.head())""",language = "python")


st.markdown("### LaTex Example : $a^2 + b^2 = c^2$")
st.latex(r"\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}")


st.success("This is a Success Message")
st.warning("This is a Warning Message")
st.error("This is a Error Message")
st.info("This is Information")

#--------------------------------------------------------------------------------

if st.button("Click Me"):
    st.write("Button Clicked")


choice = st.radio("Choose an Option: ",["Ronaldo","Messi","Neymar","Pele","Maradona"])
st.write("Your Choice: ",choice)


agree = st.checkbox("I Agree to all Terms and Conditions")
if agree:
    st.write("Thanks for Agreeing!")


genre = st.selectbox("Pick a Genre: ",["Thriller","Romance","Adventure","Fictional"])
st.write("Your Choice: ",genre)


sports = st.multiselect("Pick a Sport: ",["Cricket","Football","Badminton","Basketball","Kabaddi"])
st.write("Your Choices: ",sports)



