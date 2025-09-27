"""
Web Page Intelligence for Bot Testing - Main Streamlit Application
================================================================

This is the main Streamlit application that provides a ChatGPT-like interface
for web page intelligence and bot testing question extraction.

Author: AI Assistant
Date: 2025
"""

import os
import streamlit as st
from datetime import datetime

# Import custom modules
from config.settings import AppConfig
from modules.web_scraper import WebPageScraper
from modules.question_extractor import QuestionExtractor
from modules.rag_processor import RAGProcessor
from modules.excel_exporter import ExcelExporter
from modules.memory_manager import MemoryManager
from utils.validators import URLValidator
from utils.helpers import format_response, log_error

# Load configuration
config = AppConfig()


class WebPageIntelligenceApp:
    """Main application class for Web Page Intelligence Bot Testing"""

    def __init__(self):
        self.scraper = WebPageScraper()
        self.question_extractor = QuestionExtractor()
        self.rag_processor = RAGProcessor()
        self.excel_exporter = ExcelExporter()
        self.memory_manager = MemoryManager()
        self.url_validator = URLValidator()

    def initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        if "extracted_questions" not in st.session_state:
            st.session_state.extracted_questions = []

        if "loaded_urls" not in st.session_state:
            st.session_state.loaded_urls = {}

        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = self.memory_manager.create_new_session()

        if "processing_status" not in st.session_state:
            st.session_state.processing_status = ""

    def render_sidebar(self):
        """Render the sidebar with session management and export options"""
        with st.sidebar:
            st.header("🤖 Bot Testing Intelligence")

            # Session Management
            st.subheader("📋 Session Management")

            if st.button("➕ New Session"):
                new_session_id = self.memory_manager.create_new_session()
                st.session_state.current_session_id = new_session_id
                st.session_state.chat_history = []
                st.session_state.loaded_urls = {}
                st.session_state.extracted_questions = []
                st.rerun()

            # Display current session info
            session_info = self.memory_manager.get_session_info(st.session_state.current_session_id)
            if session_info:
                st.write(f"**Session:** {session_info.name}")
                st.write(f"**Created:** {session_info.created_at}")
                st.write(f"**URLs Processed:** {len(st.session_state.loaded_urls)}")
                st.write(f"**Questions Extracted:** {len(st.session_state.extracted_questions)}")

            st.divider()

            # Export Options
            st.subheader("📊 Export Options")

            if st.session_state.extracted_questions:
                if st.button("📥 Export Questions to Excel"):
                    try:
                        with st.spinner("Exporting to Excel..."):
                            excel_path = self.excel_exporter.export_questions(
                                st.session_state.extracted_questions,
                                session_id=st.session_state.current_session_id
                            )

                        st.success(f"✅ Questions exported successfully!")

                        # Provide download link
                        with open(excel_path, "rb") as file:
                            st.download_button(
                                label="📁 Download Excel File",
                                data=file.read(),
                                file_name=os.path.basename(excel_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"❌ Export failed: {str(e)}")
                        log_error("Excel Export Error", e)
            else:
                st.info("No questions extracted yet. Process some URLs first!")

            st.divider()

            # URLs Status
            if st.session_state.loaded_urls:
                st.subheader("🔗 Loaded URLs")
                for i, (url, data) in enumerate(st.session_state.loaded_urls.items(), 1):
                    status = "✅" if data.get("processed", False) else "⏳"
                    domain = self.url_validator.extract_domain(url)
                    st.write(f"{status} {i}. {domain}")
                    if data.get("hyperlinks_count", 0) > 0:
                        st.caption(f"   └─ {data['hyperlinks_count']} hyperlinks processed")

    
    def render_main_interface(self):
        """Render the main chat interface"""
        st.title("🌐 Web Page Intelligence for Bot Testing")
        st.markdown("**Extract Golden Questions and Expected Responses from web pages for bot testing**")

        # Display processing status
        if st.session_state.processing_status:
            st.info(st.session_state.processing_status)
            '''

        # URL input and process button
        url = st.text_input("Enter URL to process")
        if st.button("Process URL"):
            if url:
                st.session_state.processing_status = "🔍 Processing URL..."
                questions = self.question_extractor.extract_questions_and_responses(url, url)
                st.session_state.extracted_questions = questions
                st.session_state.processing_status = ""

                if questions:
                    df = self.excel_exporter._prepare_questions_data(questions)
                    st.download_button(
                        label="📥 Download Excel",
                        data=df.to_csv(index=False),
                        file_name="extracted_questions.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No questions extracted.")
            else:
                st.warning("Please enter a valid URL before processing.")
                '''

        # Chat History Display
        chat_container = st.container()
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
                        if "questions" in message and message["questions"]:
                            with st.expander(f"📝 Extracted Questions ({len(message['questions'])})"):
                                for j, question in enumerate(message["questions"], 1):
                                    st.write(f"**Q{j}:** {question['question']}")
                                    if question.get("expected_response"):
                                        st.write(f"**Expected Response:** {question['expected_response']}")
                                    st.divider()


    def process_url_input(self, user_input: str) -> dict:
        """Process URL input and extract questions (synchronous)"""
        result = {"success": False, "message": "", "questions": [], "urls_processed": []}

        try:
            urls = self.url_validator.extract_urls_from_text(user_input)
            print(f"[DEBUG] URLs extracted: {urls}")  # Log URLs found
            if not urls:
                result["message"] = "No valid URLs found in your input."
                return result

            st.session_state.processing_status = "🔍 Analyzing and scraping web pages..."
            all_questions = []
            processed_urls = []

            for url in urls:
                print(f"[DEBUG] Processing URL: {url}")
                if url in st.session_state.loaded_urls:
                    print(f"[DEBUG] URL already processed: {url}")
                    st.session_state.processing_status = f"⏭️ URL already processed: {self.url_validator.extract_domain(url)}"
                    continue

                st.session_state.processing_status = f"🌐 Scraping: {self.url_validator.extract_domain(url)}..."
                scraping_result = self.scraper.scrape_page_with_hyperlinks(url)
                print(f"[DEBUG] Scraping result: {scraping_result}")

                if scraping_result["success"]:
                    st.session_state.processing_status = f"🧠 Extracting questions from {self.url_validator.extract_domain(url)}..."
                    questions = self.question_extractor.extract_questions_and_responses(
                        scraping_result["content"], url
                    )

                    st.session_state.loaded_urls[url] = {
                        "content": scraping_result["content"],
                        "hyperlinks": scraping_result.get("hyperlinks", []),
                        "hyperlinks_count": len(scraping_result.get("hyperlinks", [])),
                        "questions": questions,
                        "processed": True,
                        "timestamp": datetime.now().isoformat()
                    }

                    self.rag_processor.add_documents(scraping_result["content"], url)

                    all_questions.extend(questions)
                    processed_urls.append(url)
                    st.session_state.processing_status = f"✅ Completed: {self.url_validator.extract_domain(url)}"
                else:
                    st.session_state.processing_status = f"❌ Failed to scrape: {self.url_validator.extract_domain(url)}"
                    print(f"[DEBUG] Failed to scrape URL: {url}")

            st.session_state.extracted_questions.extend(all_questions)
            st.session_state.processing_status = ""

            if processed_urls:
                result.update({
                    "success": True,
                    "message": f"Processed {len(processed_urls)} URL(s), extracted {len(all_questions)} questions.",
                    "questions": all_questions,
                    "urls_processed": processed_urls
                })
            else:
                result["message"] = "No new URLs processed."

        except Exception as e:
            st.session_state.processing_status = ""
            result["message"] = f"Error while processing: {str(e)}"
            log_error("URL Processing Error", e)

        return result

    def handle_question_input(self, question: str) -> str:
        """Handle general questions using RAG (synchronous)"""
        try:
            if not st.session_state.loaded_urls:
                response = self.rag_processor.get_general_response(question, st.session_state.chat_history)
            else:
                response = self.rag_processor.query_with_context(question, st.session_state.chat_history)
            return format_response(response)
        except Exception as e:
            log_error("Question Processing Error", e)
            return f"Error while processing your question: {str(e)}"

    def process_user_input(self, user_input: str):
        """Process user input (synchronous)"""
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })

        if self.url_validator.contains_urls(user_input):
            result = self.process_url_input(user_input)
            response_message = {
                "role": "assistant",
                "content": result["message"],
                "timestamp": datetime.now().isoformat()
            }
            if result["questions"]:
                response_message["questions"] = result["questions"]
            st.session_state.chat_history.append(response_message)
        else:
            response = self.handle_question_input(user_input)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })

        self.memory_manager.save_conversation(
            st.session_state.current_session_id,
            st.session_state.chat_history
        )

    def run(self):
        """Main application run function"""
        st.set_page_config(
            page_title="Web Page Intelligence for Bot Testing",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        self.initialize_session_state()
        self.render_sidebar()
        self.render_main_interface()

        if prompt := st.chat_input("Enter a webpage URL or ask about loaded content..."):
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                try:
                    self.process_user_input(prompt)

                    if st.session_state.chat_history:
                        latest_response = st.session_state.chat_history[-1]
                        if latest_response["role"] == "assistant":
                            st.write(latest_response["content"])
                            if "questions" in latest_response and latest_response["questions"]:
                                with st.expander(f"📝 Extracted Questions ({len(latest_response['questions'])})"):
                                    for i, q in enumerate(latest_response["questions"], 1):
                                        st.write(f"**Q{i}:** {q['question']}")
                                        if q.get("expected_response"):
                                            st.write(f"**Expected Response:** {q['expected_response']}")
                                        st.divider()
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    log_error("Main Processing Error", e)

        # Instructions
        with st.expander("ℹ️ How to Use"):
            st.markdown("""
            **This tool helps you extract Golden Questions and Expected Responses from web pages for bot testing.**

            🔗 **URL Processing:** Paste any webpage URL to scrape content. System follows hyperlinks for comprehensive analysis.
            💬 **Chat Interface:** Ask questions about loaded content. System uses RAG for accurate responses.
            📊 **Export:** Export all extracted questions to Excel. Download directly from sidebar.
            """)


# Main execution
if __name__ == "__main__":
    app = WebPageIntelligenceApp()
    app.run()
