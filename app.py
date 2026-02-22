import streamlit as st
import os
import json
from datetime import datetime, timedelta
from src.core.engine import ChatEngine
from src.utils.logger import log_info, log_error

def save_feedback(name, feedback):
    """Saves user feedback to Google Sheets (if configured) or local JSON."""
    timestamp = datetime.now().isoformat()
    
    # 1. Try Google Sheets
    if "gcp_service_account" in st.secrets:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            client = gspread.authorize(creds)
            
            # Open the sheet
            # 1. Try by ID (most robust)
            sheet_id = st.secrets["gcp_service_account"].get("sheet_id")
            if sheet_id:
                try:
                    sheet = client.open_by_key(sheet_id).sheet1
                except Exception as e:
                     log_error(f"Failed to open by ID {sheet_id}: {e}")
                     raise
            else:
                # 2. Fallback to Name
                sheet_name = st.secrets["gcp_service_account"].get("sheet_name", "MCMP Feedback")
                try:
                    sheet = client.open(sheet_name).sheet1
                except gspread.SpreadsheetNotFound:
                    # Optional: create if not found, but requires Drive write scope/logic
                    log_error(f"Google Sheet '{sheet_name}' not found. Fallback to JSON.")
                    raise
                
            sheet.append_row([timestamp, name, feedback])
            log_info(f"Feedback saved to Google Sheet: {sheet_name}")
            return
        except Exception as e:
            log_error(f"Failed to save to Google Sheets: {e}")
            # Fall through to JSON

    # 2. Local JSON Fallback
    feedback_file = "data/feedback.json"
    os.makedirs("data", exist_ok=True)
    
    entry = {
        "timestamp": timestamp,
        "name": name,
        "feedback": feedback
    }
    
    if os.path.exists(feedback_file):
        with open(feedback_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
        
    data.append(entry)
    
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def main():
    st.set_page_config(
        page_title="Leopold - The MCMP Chatbot",
        page_icon="🎓",
        layout="wide"
    )

    # Custom CSS to widen sidebar and adjust chat container
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            min-width: 450px;
            max-width: 500px;
        }
        .stMainBlockContainer {
            max-width: 900px;
            margin: 0 auto;
            padding-left: 3rem;
            padding-right: 3rem;
        }
        [data-testid="stChatInput"] {
            max-width: 900px;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Leopold - The MCMP Chatbot")
    st.markdown("Ask me anything about the Munich Center for Mathematical Philosophy: our research, people, history, and upcoming events.\n\nThis chatbot uses LLM + structured data tools over the MCMP website ([README](https://github.com/IgnacioOQ/mcmp_chatbot/blob/main/README.md)). It is still very much a demo and it will lack knowledge, but it should be able to provide accurate and up to date information.\n\nPlease use the feedback form on the left to leave comments, it will help improve the bot.")



    # Sidebar for configuration
    with st.sidebar:
        # 1. Monthly Calendar at the top
        import calendar
        
        # Initialize calendar month/year in session state
        if "cal_year" not in st.session_state:
            st.session_state.cal_year = datetime.now().year
        if "cal_month" not in st.session_state:
            st.session_state.cal_month = datetime.now().month
        
        cal_year = st.session_state.cal_year
        cal_month = st.session_state.cal_month
        
        # Navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀", key="prev_month", use_container_width=True):
                if cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
        with col2:
            month_name = calendar.month_name[cal_month]
            st.markdown(f"<h4 style='text-align: center; margin: 0; padding: 8px 0;'>{month_name} {cal_year}</h4>", unsafe_allow_html=True)
        with col3:
            if st.button("▶", key="next_month", use_container_width=True):
                if cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()
        
        # Build calendar HTML
        today = datetime.now().date()
        cal = calendar.Calendar(firstweekday=0)  # Monday start
        month_days = cal.monthdayscalendar(cal_year, cal_month)
        
        # Load events to highlight days with events
        event_days = set()
        try:
            with open("data/raw_events.json", "r") as f:
                raw_events = json.load(f)
            for event in raw_events:
                date_str = event.get("metadata", {}).get("date")
                if date_str:
                    try:
                        ev_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if ev_date.year == cal_year and ev_date.month == cal_month:
                            event_days.add(ev_date.day)
                    except ValueError:
                        pass
        except:
            pass
        
        # Custom CSS for calendar styling
        st.markdown("""
        <style>
        /* Calendar container styling */
        .calendar-wrapper {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 8px;
        }
        /* Style the day header row */
        .day-headers {
            display: flex;
            justify-content: space-around;
            margin-bottom: 8px;
        }
        .day-header {
            flex: 1;
            text-align: center;
            font-weight: 600;
            font-size: 11px;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 6px 0;
        }
        /* Base style for ALL calendar buttons (enabled and disabled) */
        /* Increased specificity to ensure it applies, but allowing overrides */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button {
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            background: #1a1a2e !important;    /* Dark background fixes Light Mode contrast */
            color: #ccd6f6 !important;
            font-size: 13px !important;
            padding: 8px 4px !important;
            min-height: 36px !important;
            height: 36px !important;
            line-height: 20px !important;
            border-radius: 4px !important;
        }
        /* Ensure disabled buttons look the same height */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button:disabled {
            opacity: 0.5 !important;
            cursor: default !important;
            background: #161625 !important; /* Slightly distinct for disabled */
        }
        /* Event day buttons - consistent dark teal base */
        [data-testid="stSidebar"] .event-day-btn button {
            background: #1a2f2f !important;    /* Dark Teal background */
            border: 1px solid rgba(100, 255, 218, 0.5) !important;
            color: #64ffda !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] .event-day-btn button:hover {
            background: #234545 !important;
        }
        /* Today highlight */
        [data-testid="stSidebar"] .today-btn button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: #fff !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4) !important;
            opacity: 1 !important;
            border: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Calendar header
        st.markdown("""
        <div class="calendar-wrapper">
            <div class="day-headers">
                <span class="day-header">Mo</span>
                <span class="day-header">Tu</span>
                <span class="day-header">We</span>
                <span class="day-header">Th</span>
                <span class="day-header">Fr</span>
                <span class="day-header">Sa</span>
                <span class="day-header">Su</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Build calendar grid using native Streamlit columns
        for week in month_days:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown("<div style='height: 36px;'></div>", unsafe_allow_html=True)
                    else:
                        is_today = day == today.day and cal_month == today.month and cal_year == today.year
                        has_event = day in event_days
                        
                        # Apply CSS class wrapper for styling
                        if has_event and is_today:
                            wrapper_class = "event-day-btn today-btn"
                        elif has_event:
                            wrapper_class = "event-day-btn"
                        elif is_today:
                            wrapper_class = "today-btn"
                        else:
                            wrapper_class = ""
                        
                        if wrapper_class:
                            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                        
                        if has_event:
                            if st.button(f"{day}", key=f"cal_{cal_year}_{cal_month}_{day}", use_container_width=True):
                                st.session_state.calendar_query_date = f"{cal_year}-{cal_month:02d}-{day:02d}"
                                st.session_state.calendar_query_formatted = datetime(cal_year, cal_month, day).strftime("%B %d, %Y")
                        else:
                            # Non-clickable day - just show the number
                            st.button(f"{day}", key=f"cal_{cal_year}_{cal_month}_{day}", use_container_width=True, disabled=True)
                        
                        if wrapper_class:
                            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 2. Feedback form
        with st.expander("💬 Give Feedback", expanded=False):
            with st.form("feedback_form"):
                name = st.text_input("Name (optional)")
                feedback = st.text_area("Your Feedback", help="Let us know what you think!")
                submitted = st.form_submit_button("Submit")
                if submitted and feedback:
                    save_feedback(name, feedback)
                    st.success("Thank you for your feedback!")

        st.markdown("---")
        
        # 3. Events this week
        st.header("📆 Events this Week")
        
        # Load and filter events
        try:
            with open("data/raw_events.json", "r") as f:
                raw_events = json.load(f)
            
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            events_this_week = []
            
            for event in raw_events:
                meta = event.get("metadata", {})
                date_str = meta.get("date")
                if not date_str:
                    continue
                    
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if start_of_week <= event_date <= end_of_week:
                        # Enhanced speaker extraction
                        speaker = meta.get("speaker")
                        title = event.get("title", "Untitled")
                        
                        if not speaker or speaker == "Unknown Speaker":
                            # Heuristic: "Talk: [Speaker Name]" or "Talk (Info): [Speaker Name]"
                            if "Talk" in title and ":" in title:
                                try:
                                    # Split by first colon and strip
                                    parts = title.split(":", 1)
                                    if len(parts) > 1:
                                        speaker = parts[1].strip()
                                except:
                                    pass
                        
                        if not speaker:
                             speaker = "Unknown Speaker"

                        # Enhanced title extraction from description
                        description = event.get("description", "")
                        if "Title:\n" in description:
                            try:
                                # Extract text after "Title:\n"
                                part_after = description.split("Title:\n", 1)[1]
                                # Stop at "Abstract"
                                if "Abstract" in part_after:
                                    real_title = part_after.split("Abstract", 1)[0].strip()
                                    # Clean up newlines if it spans multiple lines
                                    if real_title:
                                        title = real_title.replace("\n", " ")
                            except:
                                pass

                        events_this_week.append({
                            "title": title,
                            "speaker": speaker,
                            "date": event_date,
                            "time": meta.get("time_start", "Time TBA"),
                            "url": event.get("url", "#")
                        })
                except ValueError:
                    continue
            
            events_this_week.sort(key=lambda x: x["date"])
            
            if not events_this_week:
                st.info("No events scheduled for this week.")
            else:
                for ev in events_this_week:
                    date_fmt = ev["date"].strftime("%A, %d")
                    st.markdown(f"**{ev['speaker']}**")
                    st.markdown(f"[{ev['title']}]({ev['url']})")
                    st.caption(f"📅 {date_fmt} at {ev['time']}")
                    st.markdown("---")
            
        except Exception as e:
            st.error(f"Could not load events: {e}")

        st.markdown("---")
        
        # 4. Configuration at the bottom
        st.header("⚙️ Configuration")
        
        # Model Selection
        model_choice = st.radio(
            "Select Model",
            options=["gemini-2.0-flash", "gemini-2.0-flash-lite"],
            index=0,
            format_func=lambda x: "Gemini 2.0 Flash (Balanced)" if x == "gemini-2.0-flash" else "Gemini 2.0 Flash-Lite (Economy)",
            help="Flash is better for complex queries. Flash-Lite is cheaper but still powerful."
        )

    # Initialize ChatEngine
    if "engine" not in st.session_state:
        # Try to get key from secrets, otherwise ChatEngine will fallback to os.getenv
        api_key = st.secrets.get("GEMINI_API_KEY") 
        st.session_state.engine = ChatEngine(provider="gemini", api_key=api_key)

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle calendar day click via session state (from button clicks)
    if "calendar_query_date" in st.session_state:
        query_formatted = st.session_state.calendar_query_formatted
        # Clear the trigger to prevent re-execution
        del st.session_state.calendar_query_date
        del st.session_state.calendar_query_formatted
        
        # Generate the prompt silently
        auto_prompt = f"What talks or events are scheduled for {query_formatted}? Please provide details about each event, including an abstract or description."
        
        # Add to chat history and generate response
        st.session_state.messages.append({"role": "user", "content": auto_prompt})
        with st.chat_message("user"):
            st.markdown(auto_prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Looking up events..."):
                response = st.session_state.engine.generate_response(auto_prompt, model_name=model_choice, chat_history=st.session_state.messages[:-1])
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # User input
    if prompt := st.chat_input("What is the next talk about?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.engine.generate_response(prompt, model_name=model_choice, chat_history=st.session_state.messages[:-1])
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
