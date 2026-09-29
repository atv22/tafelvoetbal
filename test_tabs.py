import streamlit as st
import streamlit.components.v1 as components
import os

st.title("Test Tabs")
tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])
with tab1:
    st.write("Hello")
    
components.html("""
    <script>
    setTimeout(function() {
        var tabs = window.parent.document.querySelectorAll('.stTabs [role="tab"]');
        var res = "";
        for (var i=0; i<tabs.length; i++) {
            res += "TAB " + i + " classes: " + tabs[i].className + "\\n";
            res += "TAB " + i + " attributes: ";
            for (var j=0; j<tabs[i].attributes.length; j++) {
                res += tabs[i].attributes[j].name + "=" + tabs[i].attributes[j].value + ", ";
            }
            res += "\\n";
        }
        var div = window.parent.document.querySelector('.stTabs > div');
        if (div) {
            res += "LIST classes: " + div.className + "\\n";
            res += "LIST attributes: ";
            for (var j=0; j<div.attributes.length; j++) {
                res += div.attributes[j].name + "=" + div.attributes[j].value + ", ";
            }
        }
        
        // Stuur dit naar python backend via api call of gewoon schrijf in de DOM zodat we het kunnen lezen
        document.body.innerHTML = "<pre id='output'>" + res + "</pre>";
    }, 1000);
    </script>
""", height=200)
