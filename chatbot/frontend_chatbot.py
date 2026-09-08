import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from backend_chatbot import (
	chatbot,
	create_conversation,
	delete_conversation,
	list_conversations,
	load_conversation,
	update_conversation,
)


st.set_page_config(
	page_title="Morrow | AI chat",
	page_icon="M",
	layout="centered",
	initial_sidebar_state="expanded",
)

st.markdown(
	"""
	<style>
		:root {
			--ink: #14213d;
			--muted: #53627a;
			--paper: #f7f4ee;
			--line: #d9d5cc;
			--coral: #e76f51;
			--mint: #d8f3dc;
		}
		.stApp {
			background-color: var(--paper);
			background-image: linear-gradient(rgba(20, 33, 61, .035) 1px, transparent 1px),
				linear-gradient(90deg, rgba(20, 33, 61, .035) 1px, transparent 1px);
			background-size: 28px 28px;
			color: var(--ink);
		}
		.stApp p, .stApp span, .stApp label, .stApp [data-testid="stMarkdownContainer"] {
			color: var(--ink);
		}
		[data-testid="stHeader"] { background: transparent; }
		[data-testid="stSidebar"] {
			background: var(--ink);
			border-right: 0;
		}
		[data-testid="stSidebar"] *,
		[data-testid="stSidebar"] p,
		[data-testid="stSidebar"] span,
		[data-testid="stSidebar"] label,
		[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #f7f4ee; }
		[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
		[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: #c4cede; }
		[data-testid="stSidebar"] hr { border-color: rgba(247, 244, 238, .18); }
		.brand-lockup { display: flex; align-items: center; gap: .7rem; margin: 1rem 0 2rem; }
		.brand-mark {
			width: 2.25rem; height: 2.25rem; display: grid; place-items: center;
			border-radius: 10px; background: var(--coral); color: white;
			font-weight: 800; font-size: 1.15rem; box-shadow: 4px 4px 0 #f4a261;
		}
		.brand-name { font-size: 1.2rem; font-weight: 800; letter-spacing: .02em; }
		.brand-note { color: #b8c4d6; font-size: .75rem; }
		.sidebar-label { color: #f4a261; text-transform: uppercase; letter-spacing: .14em; font-size: .68rem; font-weight: 800; }
		.stButton > button[kind="primary"] { background: var(--coral); border: 0; color: white; }
		.stButton > button[kind="primary"]:hover { background: #d95d40; color: white; }
		.app-shell { max-width: 760px; margin: 0 auto; }
		.app-kicker { color: var(--coral) !important; text-transform: uppercase; letter-spacing: .16em; font-size: .72rem; font-weight: 800; margin-top: 2.5rem; }
		.app-title { margin: .45rem 0 .2rem; color: var(--ink) !important; font-size: clamp(2rem, 6vw, 3.25rem); line-height: 1.02; font-weight: 850; letter-spacing: -.045em; }
		.app-subtitle { margin-bottom: 1.7rem; color: var(--muted) !important; font-size: 1.03rem; }
		.status-line { display: inline-flex; align-items: center; gap: .45rem; padding: .35rem .7rem; border: 1px solid var(--line); border-radius: 999px; color: var(--muted) !important; background: rgba(255,255,255,.75); font-size: .78rem; }
		.status-line * { color: var(--muted) !important; }
		.status-dot { width: .45rem; height: .45rem; border-radius: 50%; background: #2a9d8f; box-shadow: 0 0 0 3px rgba(42,157,143,.16); }
		.welcome-panel { margin: 2.3rem 0 1rem; padding: 1.3rem 1.4rem; border: 1px solid var(--line); border-left: 5px solid var(--coral); background: rgba(255,255,255,.62); box-shadow: 8px 8px 0 rgba(20,33,61,.08); }
		.welcome-panel strong { color: var(--ink) !important; }
		.welcome-panel p { color: var(--muted) !important; margin: .35rem 0 0; }
		[data-testid="stChatMessage"] { border-radius: 16px; padding: .8rem 1rem; border: 1px solid var(--line); box-shadow: 0 4px 14px rgba(20,33,61,.05); }
		[data-testid="stChatMessage"] p,
		[data-testid="stChatMessage"] li,
		[data-testid="stChatMessage"] code { color: var(--ink) !important; font-size: 1rem; line-height: 1.65; }
		[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { background: var(--mint); border-color: #b7dfc0; }
		[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { background: rgba(255,255,255,.8); }
		.stChatInput { padding-bottom: 1rem; }
		[data-testid="stChatInput"] { border-color: var(--ink); background: rgba(255,255,255,.9); }
		[data-testid="stChatInput"] textarea { color: var(--ink) !important; caret-color: var(--coral); }
		[data-testid="stChatInput"] textarea::placeholder { color: #68758a !important; opacity: 1; }
		[data-testid="stChatInput"] button svg { color: var(--ink); }
	</style>
	""",
	unsafe_allow_html=True,
)


def start_new_chat() -> None:
	thread_id = str(uuid.uuid4())
	create_conversation(thread_id)
	st.session_state.thread_id = thread_id
	st.session_state.messages = []


if "thread_id" not in st.session_state:
	conversations = list_conversations()
	if conversations:
		st.session_state.thread_id = conversations[0]["thread_id"]
	else:
		start_new_chat()
if "messages" not in st.session_state:
	st.session_state.messages = load_conversation(st.session_state.thread_id)

config = {"configurable": {"thread_id": st.session_state.thread_id}}

with st.sidebar:
	st.markdown(
		'<div class="brand-lockup"><div class="brand-mark">M</div><div><div class="brand-name">Morrow</div><div class="brand-note">a thoughtful AI companion</div></div></div>',
		unsafe_allow_html=True,
	)
	st.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
	if st.button("New conversation", use_container_width=True, type="primary"):
		start_new_chat()
		st.rerun()
	st.divider()
	st.markdown('<div class="sidebar-label">Saved chats</div>', unsafe_allow_html=True)
	for conversation in list_conversations():
		is_current = conversation["thread_id"] == st.session_state.thread_id
		button_label = ("● " if is_current else "○ ") + conversation["title"]
		if st.button(button_label, key=f"open-{conversation['thread_id']}", use_container_width=True):
			st.session_state.thread_id = conversation["thread_id"]
			st.session_state.messages = load_conversation(st.session_state.thread_id)
			st.rerun()
	st.divider()
	with st.expander("Manage current chat"):
		new_title = st.text_input(
			"Conversation name",
			value=next(
				(
					item["title"]
					for item in list_conversations()
					if item["thread_id"] == st.session_state.thread_id
				),
				"New conversation",
			),
			key="conversation-title",
		)
		if st.button("Save name", use_container_width=True):
			update_conversation(st.session_state.thread_id, new_title.strip() or "New conversation")
			st.rerun()
		if st.button("Delete conversation", use_container_width=True):
			delete_conversation(st.session_state.thread_id)
			start_new_chat()
			st.rerun()
	st.caption("Chats resume automatically from SQLite storage.")

st.markdown('<div class="app-shell">', unsafe_allow_html=True)
st.markdown('<div class="app-kicker">Personal intelligence, quietly delivered</div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">What is on your mind?</div>', unsafe_allow_html=True)
st.markdown(
	'<div class="app-subtitle">Ask anything. Keep the thread going.</div><div class="status-line"><span class="status-dot"></span> Morrow is ready</div>',
	unsafe_allow_html=True,
)
if not st.session_state.messages:
	st.markdown(
		'<div class="welcome-panel"><strong>Start somewhere interesting.</strong><p>Plan a trip, untangle an idea, or ask a question you have been carrying around.</p></div>',
		unsafe_allow_html=True,
	)

for message in st.session_state.messages:
	with st.chat_message(message["role"]):
		st.markdown(message["content"])

user_input = st.chat_input("Message your assistant...")
if user_input:
	st.session_state.messages.append({"role": "user", "content": user_input})
	conversation = next(
		(
			item
			for item in list_conversations()
			if item["thread_id"] == st.session_state.thread_id
		),
		None,
	)
	if conversation and conversation["title"] == "New conversation":
		update_conversation(st.session_state.thread_id, user_input[:42])
	with st.chat_message("user"):
		st.markdown(user_input)

	with st.chat_message("assistant"):
		response_placeholder = st.empty()
		response = ""
		try:
			for message_chunk, _metadata in chatbot.stream(
				{
					"user_input": [HumanMessage(content=user_input)],
					"bot_response": [],
				},
				config=config,
				stream_mode="messages",
			):
				if message_chunk.content:
					if isinstance(message_chunk.content, str):
						response += message_chunk.content
					else:
						response += "".join(
							part.get("text", "")
							for part in message_chunk.content
							if isinstance(part, dict)
						)
					response_placeholder.markdown(response)
		except Exception as error:
			response = (
				"I couldn't reach the language model. Check your `GROQ_API_KEY` "
				f"and model configuration.\n\n`{error}`"
			)
			response_placeholder.markdown(response)

	st.session_state.messages.append({"role": "assistant", "content": response})
	update_conversation(st.session_state.thread_id)

st.markdown('</div>', unsafe_allow_html=True)
