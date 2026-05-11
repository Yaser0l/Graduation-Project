import React, { useContext, useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import { LanguageContext } from '../store/AppContext';
import { api } from '../services/api';
import { Send, Zap, MessageCircle, FileText, Loader } from 'lucide-react';
import styles from './Chat.module.css';

const MarkdownRenderer = ({ text }) => {
  if (!text) return null;
  const blocks = text.split(/\n\n+/);
  
  return blocks.map((block, bIdx) => {
    const trimmed = block.trim();
    if (!trimmed) return null;

    if (trimmed.startsWith('###')) {
      return <h3 key={bIdx} className={styles.mdHeader}>{renderInlines(trimmed.replace(/^###\s*/, ''))}</h3>;
    }

    if (/^---+$/.test(trimmed)) {
      return <hr key={bIdx} />;
    }

    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);

    if (lines.length > 0 && lines.every((line) => /^[-*]\s+/.test(line))) {
      return (
        <ul key={bIdx} className={styles.mdList}>
          {lines.map((item, iIdx) => (
            <li key={iIdx}>{renderInlines(item.replace(/^[*|-]\s*/, ''))}</li>
          ))}
        </ul>
      );
    }

    if (lines.length > 0 && lines.every((line) => /^\d+\.\s+/.test(line))) {
      return (
        <ol key={bIdx} className={styles.mdList}>
          {lines.map((item, iIdx) => (
            <li key={iIdx}>{renderInlines(item.replace(/^\d+\.\s*/, ''))}</li>
          ))}
        </ol>
      );
    }

    return <p key={bIdx} className={styles.mdPara}>{renderInlines(block)}</p>;
  });
};

const renderInlines = (text) => {
  const normalized = String(text || '')
    .replace(/\*\*\s+\*\*/g, ' ')
    .replace(/__\s+__/g, ' ')
    .replace(/\*{3,}/g, '**');

  const out = [];
  const pattern = /(\*\*|__)(.+?)\1/g;
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = pattern.exec(normalized)) !== null) {
    const [full, , content] = match;
    if (match.index > lastIndex) {
      out.push(normalized.slice(lastIndex, match.index));
    }
    out.push(<strong key={`s-${key}`}>{content}</strong>);
    key += 1;
    lastIndex = match.index + full.length;
  }

  if (lastIndex < normalized.length) {
    const tail = normalized.slice(lastIndex)
      .replace(/(^|\s)\*\*(?=\s|$)/g, '$1')
      .replace(/(^|\s)__(?=\s|$)/g, '$1');
    out.push(tail);
  }

  return out;
};

export default function Chat() {
  const { language } = useContext(LanguageContext);
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const queryReportId = searchParams.get('reportId');
  const reportId = queryReportId || localStorage.getItem('lastChatReportId');

  const [messages, setMessages] = useState([]);
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isReporting, setIsReporting] = useState(false);
  const [currentReport, setCurrentReport] = useState(null);
  const scrollRef = useRef(null);
  const streamBufferRef = useRef([]);
  const streamTimerRef = useRef(null);
  const streamMessageIdRef = useRef(null);
  const streamModeRef = useRef('word');
  const pendingFinalTextRef = useRef(null);

  const STREAM_DISPLAY_MODE = 'word'; // switch to 'char' for character-by-character reveal

  const getChatCacheKey = (id) => `chat_cache_${id}`;

  const splitForReveal = (text, mode = 'word') => {
    if (!text) return [];
    if (mode === 'char') return Array.from(text);
    return text.match(/\S+\s*|\s+/g) || [text];
  };

  const stopStreamReveal = () => {
    if (streamTimerRef.current) {
      clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }
    streamBufferRef.current = [];
    streamMessageIdRef.current = null;
    pendingFinalTextRef.current = null;
  };

  const startStreamReveal = (messageId, mode = 'word') => {
    stopStreamReveal();
    streamMessageIdRef.current = messageId;
    streamModeRef.current = mode;

    const intervalMs = mode === 'char' ? 14 : 45;
    streamTimerRef.current = setInterval(() => {
      const nextChunk = streamBufferRef.current.shift();
      if (!streamMessageIdRef.current) return;

      if (!nextChunk) {
        if (pendingFinalTextRef.current !== null) {
          const targetId = streamMessageIdRef.current;
          const finalText = pendingFinalTextRef.current;
          setMessages(prev => prev.map(m => (
            m.id === targetId ? { ...m, text: finalText || m.text } : m
          )));
          stopStreamReveal();
        }
        return;
      }

      setMessages(prev => prev.map(m => (
        m.id === streamMessageIdRef.current ? { ...m, text: `${m.text}${nextChunk}` } : m
      )));
    }, intervalMs);
  };

  const pushStreamChunk = (chunkText) => {
    streamBufferRef.current.push(...splitForReveal(chunkText, streamModeRef.current));
  };

  const finalizeStreamMessage = (finalText) => {
    if (!streamMessageIdRef.current) return;
    pendingFinalTextRef.current = finalText || '';

    // If there is no buffered content left, finalize immediately.
    if (streamBufferRef.current.length === 0) {
      const targetId = streamMessageIdRef.current;
      const doneText = pendingFinalTextRef.current;
      setMessages(prev => prev.map(m => (
        m.id === targetId ? { ...m, text: doneText || m.text } : m
      )));
      stopStreamReveal();
    }
  };

  useEffect(() => {
    if (queryReportId) {
      localStorage.setItem('lastChatReportId', queryReportId);
    }
  }, [queryReportId]);

  // Load History & Report Details
  useEffect(() => {
    const initChat = async () => {
      if (!reportId) {
        setMessages([{
          id: 'initial',
          sender: 'ai',
          text: language === 'ar' 
            ? 'مرحباً! كيف يمكنني مساعدتك اليوم؟ يرجى اختيار تقرير لمناقشته.'
            : 'Hello! How can I assist you today? Please select a diagnostic report to discuss.'
        }]);
        return;
      }

      try {
        let hasCachedMessages = false;
        const cached = localStorage.getItem(getChatCacheKey(reportId));
        if (cached) {
          const cachedMessages = JSON.parse(cached);
          if (Array.isArray(cachedMessages) && cachedMessages.length > 0) {
            setMessages(cachedMessages);
            hasCachedMessages = true;
          }
        }

        const reportData = await api.diagnostics.get(reportId);
        setCurrentReport(reportData);

        const historyData = await api.chat.history(reportId);
        
        let initialMessages = [];
        
        // Always prepend the report explanation as the first AI context
        if (reportData.llm_explanation) {
          initialMessages.push({
            id: 'report-context',
            sender: 'ai',
            text: reportData.llm_explanation
          });
        }

        if (historyData.messages && historyData.messages.length > 0 && !hasCachedMessages) {
          const mapped = historyData.messages.map((m, idx) => ({
            id: `h-${idx}`,
            sender: m.role === 'user' ? 'user' : 'ai',
            text: m.content
          }));
          const merged = [...initialMessages, ...mapped];
          setMessages(merged);
          localStorage.setItem(getChatCacheKey(reportId), JSON.stringify(merged));
        } else if (!hasCachedMessages) {
          const initial = [
            ...initialMessages,
            {
              id: 'initial',
              sender: 'ai',
              text: language === 'ar' 
                ? `الأنظمة متصلة. أنا مستعد لمناقشة تقرير ${reportData.dtc_codes?.join(', ') || ''} معك.`
                : `Systems interfaced. I am ready to discuss the diagnostic report for ${reportData.dtc_codes?.join(', ') || ''} with you.`
            }
          ];
          setMessages(initial);
          localStorage.setItem(getChatCacheKey(reportId), JSON.stringify(initial));
        }
      } catch (err) {
        console.error("Failed to initialize chat:", err);
      }
    };
    initChat();
  }, [reportId]);

  useEffect(() => {
    if (!reportId || messages.length === 0) return;
    localStorage.setItem(getChatCacheKey(reportId), JSON.stringify(messages));
  }, [messages, reportId]);

  useEffect(() => {
    return () => stopStreamReveal();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text) => {
    if (!text.trim() || isLoading || isReporting || !reportId) return;

    const userMessage = { id: Date.now().toString(), sender: 'user', text };
    const aiMessageId = `${Date.now()}-stream-ai`;
    setMessages(prev => [...prev, userMessage]);
    setInputVal('');
    setIsLoading(true);
    setMessages(prev => [...prev, { id: aiMessageId, sender: 'ai', text: '' }]);
    startStreamReveal(aiMessageId, STREAM_DISPLAY_MODE);

    try {
      const response = await api.chat.send(reportId, text, {
        streamMode: 'word',
        streamChunkSize: 3,
        onToken: (chunk) => pushStreamChunk(chunk),
      });
      finalizeStreamMessage(response?.reply || '');
    } catch (err) {
      console.error("Failed to send message:", err);
      finalizeStreamMessage(language === 'ar'
        ? 'عذراً، حدث خطأ أثناء الاتصال بالخادم.'
        : 'Sorry, an error occurred while connecting to the engine.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFullReport = async () => {
    if (isReporting || isLoading || !reportId) return;
    setIsReporting(true);
    const reportMessageId = `fr-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: reportMessageId,
      sender: 'ai',
      text: ''
    }]);
    startStreamReveal(reportMessageId, STREAM_DISPLAY_MODE);
    try {
      const result = await api.diagnostics.fullReport(reportId, language, {
        streamMode: 'word',
        streamChunkSize: 4,
        onToken: (chunk) => pushStreamChunk(chunk),
      });
      finalizeStreamMessage(result?.explanation || (language === 'ar' ? 'لم يتم إنشاء التقرير.' : 'No report was generated.'));
    } catch (err) {
      finalizeStreamMessage(language === 'ar'
        ? 'فشل إنشاء التقرير الشامل. يرجى المحاولة مجدداً.'
        : 'Failed to generate full report. Please try again.');
    } finally {
      setIsReporting(false);
    }
  };

  const chips = useMemo(() => {
    if (!currentReport || !currentReport.dtc_codes) return [];
    const firstCode = currentReport.dtc_codes[0];
    return [
      { id: "q1", textEn: `Explain ${firstCode} simply.`, textAr: `اشرح عطل ${firstCode} ببساطة.` },
      { id: "q2", textEn: `What usually causes ${firstCode}?`, textAr: `ما الأسباب الشائعة لعطل ${firstCode}؟` },
      { id: "q3", textEn: `How urgent is ${firstCode} right now?`, textAr: `ما مدى خطورة ${firstCode} حالياً؟` },
    ];
  }, [currentReport]);

  return (
    <motion.div className={styles.container} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {!reportId && (
        <div className={styles.warningBanner}>
          <MessageCircle size={16} />
          <span>{language === 'ar' ? 'برجاء فتح التقرير من قسم التشخيص لمناقشته.' : 'Please open a report from Diagnostics to discuss it.'}</span>
        </div>
      )}

      <div className={styles.chatArea} ref={scrollRef}>
        <AnimatePresence initial={false}>
          {messages.map(msg => (
            <motion.div 
              key={msg.id}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`${styles.messageWrapper} ${msg.sender === 'user' ? styles.userWrap : styles.aiWrap}`}
            >
              {msg.sender === 'ai' && (
                <div className={styles.aiAvatar}>
                  <Zap size={16} className={styles.glowIcon} />
                </div>
              )}
              <div className={`${styles.bubble} ${styles[msg.sender]}`}>
                <MarkdownRenderer text={msg.text} />
              </div>
            </motion.div>
          ))}
          {isLoading && !streamMessageIdRef.current && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={styles.aiWrap}>
               <div className={styles.aiAvatar}><Zap size={16} className={styles.glowIcon} /></div>
               <div className={`${styles.bubble} ${styles.ai}`}>...</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className={styles.interactionZone}>
        <div className={styles.chipsContainer}>
          {chips.map(chip => (
            <button 
              key={chip.id} 
              className={styles.chip} 
              disabled={!reportId || isLoading || isReporting}
              onClick={() => handleSend(language === 'ar' ? chip.textAr : chip.textEn)}
            >
              {language === 'ar' ? chip.textAr : chip.textEn}
            </button>
          ))}
        </div>
        <div className={styles.inputStack}>
          <input 
            type="text" 
            className={styles.input}
            placeholder={language === 'ar' ? 'رسالة...' : 'Transmit message...'}
            value={inputVal}
            disabled={!reportId || isLoading || isReporting}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend(inputVal)}
          />
          <button 
            className={styles.reportBtn} 
            onClick={handleFullReport} 
            disabled={!reportId || isReporting || isLoading}
            title={language === 'ar' ? 'تقرير شامل' : 'Full Report'}
          >
            {isReporting ? <Loader size={20} className={styles.spinIcon} /> : <FileText size={20} />}
          </button>
          <button className={styles.sendBtn} onClick={() => handleSend(inputVal)} disabled={!reportId || isLoading || isReporting}>
            <Send size={20} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
