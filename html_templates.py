css = """
<style>
    /* User Chat Message - Smooth Dark Blue Bubble */
    .st-emotion-cache-janbn0 {
        background-color: #2b313e;
        color: #ffffff;
        border-radius: 15px 15px 0px 15px;
        padding: 10px 15px;
        margin-bottom: 10px;
    }

    /* AI Chat Message - Premium Purple/Indigo Bubble */
    .st-emotion-cache-4oy321 {
        background-color: #3b3f54;
        color: #e0e0e0;
        border-radius: 15px 15px 15px 0px;
        padding: 10px 15px;
        margin-bottom: 10px;
    }

    /* Message card hover effects and transition */
    .stChatMessage {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border-radius: 15px;
    }
    .stChatMessage:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* Sidebar Width Customization */
    section[data-testid="stSidebar"] {
        width: 380px !important;
    }

    /* Sidebar Footer Styling */
    .sidebar-footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #4a5568;
        font-size: 0.8rem;
        color: #a0aec0;
    }

    /* Elegant Divider Line */
    .divider-line {
        margin: 1.5rem 0;
        border-bottom: 1px solid #4a5568;
    }

    /* Modern Webkit Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #4a5568;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #718096;
    }
</style>
"""