import { useState, useRef, useEffect } from "react";
import {
  Bot,
  Send,
  Sparkles,
  CheckCircle2,
  Users,
  BarChart3,
  UserRoundSearch,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function AgentPanel() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);

  const conversationRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop =
        conversationRef.current.scrollHeight;
    }
  }, [conversation, loading]);

  const sendMessage = async (messageToSend = message) => {
    const text = messageToSend.trim();

    if (!text || loading) {
      return;
    }

    setConversation((previous) => [
      ...previous,
      {
        role: "user",
        content: text,
      },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          year: 2026,
          month: 11,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Agent request failed."
        );
      }

      setConversation((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.message,
        },
      ]);
    } catch (error) {
      setConversation((previous) => [
        ...previous,
        {
          role: "assistant",
          content: error.message,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);

      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const clearConversation = () => {
    setConversation([]);
    setMessage("");

    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  return (
    <section className="agent-panel">

      {/* =====================================================
          HEADER
      ====================================================== */}
      <div className="agent-panel-header">

        <div className="agent-title-section">

          <div className="agent-avatar">
            <Bot size={22} strokeWidth={2.2} />
          </div>

          <div>
            <div className="agent-title-row">
              <h2>Roster Copilot</h2>

              <span className="agent-online">
                <span className="agent-online-dot"></span>
                AI Online
              </span>
            </div>

            <p>
              Your AI assistant for the November 2026 workforce roster
            </p>
          </div>

        </div>

        {conversation.length > 0 && (
          <button
            className="agent-clear-button"
            onClick={clearConversation}
          >
            Clear chat
          </button>
        )}

      </div>

      {/* =====================================================
          CHAT AREA
      ====================================================== */}
      <div
        className="agent-conversation"
        ref={conversationRef}
      >

        {conversation.length === 0 ? (

          <div className="agent-welcome">

            <div className="agent-welcome-icon">
              <Sparkles size={28} />
            </div>

            <h3>
              How can I help with your roster?
            </h3>

            <p>
              Ask me to validate, analyze, or understand your
              November 2026 roster.
            </p>

            {/* Suggested questions */}
            <div className="agent-suggestions">

              <button
                onClick={() =>
                  sendMessage("Is my roster valid?")
                }
              >
                <CheckCircle2 size={17} />
                <span>
                  Is my roster valid?
                </span>
              </button>

              <button
                onClick={() =>
                  sendMessage("Who is potentially overloaded?")
                }
              >
                <BarChart3 size={17} />
                <span>
                  Who is overloaded?
                </span>
              </button>

              <button
                onClick={() =>
                  sendMessage("Who is underutilized?")
                }
              >
                <Users size={17} />
                <span>
                  Who is underutilized?
                </span>
              </button>

              <button
                onClick={() =>
                  sendMessage(
                    "Find cross-skilled employees who could help redistribute workload."
                  )
                }
              >
                <UserRoundSearch size={17} />
                <span>
                  Find cross-skilled employees
                </span>
              </button>

            </div>

          </div>

        ) : (

          <div className="agent-message-list">

            {conversation.map((item, index) => (

              <div
                key={index}
                className={
                  item.role === "user"
                    ? "agent-message-row user-row"
                    : "agent-message-row assistant-row"
                }
              >

                {item.role === "assistant" && (
                  <div className="message-avatar">
                    <Bot size={17} />
                  </div>
                )}

                <div
                  className={
                    item.role === "user"
                      ? "agent-message user-message"
                      : item.error
                        ? "agent-message assistant-message error-message"
                        : "agent-message assistant-message"
                  }
                >
                  {item.content}
                </div>

              </div>

            ))}

            {loading && (

              <div className="agent-message-row assistant-row">

                <div className="message-avatar">
                  <Bot size={17} />
                </div>

                <div className="agent-message assistant-message typing-message">

                  <span></span>
                  <span></span>
                  <span></span>

                </div>

              </div>

            )}

          </div>

        )}

      </div>

      {/* =====================================================
          INPUT AREA
      ====================================================== */}
      <div className="agent-input-section">

        <div className="agent-input-wrapper">

          <textarea
            ref={inputRef}
            value={message}
            onChange={(event) =>
              setMessage(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your roster..."
            disabled={loading}
            rows={1}
          />

          <button
            className="agent-send-button"
            onClick={() => sendMessage()}
            disabled={loading || !message.trim()}
            aria-label="Send message"
          >
            <Send size={18} />
          </button>

        </div>

        <div className="agent-input-footer">
          <span>
            Press Enter to send
          </span>

          <span>
            AI recommendations should be validated before changes are applied.
          </span>
        </div>

      </div>

    </section>
  );
}