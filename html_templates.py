css = """
    <style>
        /* Base Container Styling */
        .main {
            background-color: #0e1117;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            width: 400px !important;
            background-color: #161b22 !important;
            border-right: 1px solid #30363d;
        }

        /* Chat Message Styling */
        .stChatMessage {
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid #30363d;
            transition: all 0.3s ease;
        }

        .stChatMessage:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }

        /* User Message */
        [data-testid="stChatMessage"]:nth-child(even) {
            background-color: #1f2937 !important;
        }

        /* AI Message */
        [data-testid="stChatMessage"]:nth-child(odd) {
            background-color: #111827 !important;
            border-left: 4px solid #3b82f6 !important;
        }

        /* Sidebar Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            height: 45px;
            white-space: pre-wrap;
            background-color: #21262d;
            border-radius: 8px 8px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
            border: 1px solid #30363d;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
        }

        /* Status Widget */
        .status-card {
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #3b82f6;
            margin-bottom: 1rem;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #0e1117;
        }
        ::-webkit-scrollbar-thumb {
            background: #30363d;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #484f58;
        }
    </style>
    """