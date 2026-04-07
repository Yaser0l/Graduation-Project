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
    if (block.startsWith('###')) {
      return <h3 key={bIdx} className={styles.mdHeader}>{block.replace(/^###\s*/, '')}</h3>;
    }
    if (block.startsWith('* ') || block.startsWith('- ')) {
      const items = block.split('\n');
      return (
        <ul key={bIdx} className={styles.mdList}>
          {items.map((item, iIdx) => (
            <li key={iIdx}>{renderInlines(item.replace(/^[*|-]\s*/, ''))}</li>
          ))}
        </ul>
      );
    }
    return <p key={bIdx} className={styles.mdPara}>{renderInlines(block)}</p>;
  });
};

const renderInlines = (text) => {
  const parts = text.split(/(\*\*.*?\*\*)/);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
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

  const getChatCacheKey = (id) => `chat_cache_${id}`;

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
        const cached = localStorage.getItem(getChatCacheKey(reportId));
        if (cached) {
          const cachedMessages = JSON.parse(cached);
          if (Array.isArray(cachedMessages) && cachedMessages.length > 0) {
            setMessages(cachedMessages);
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

        if (historyData.messages && historyData.messages.length > 0) {
          const mapped = historyData.messages.map((m, idx) => ({
            id: `h-${idx}`,
            sender: m.role === 'user' ? 'user' : 'ai',
            text: m.content
          }));
          const merged = [...initialMessages, ...mapped];
          setMessages(merged);
          localStorage.setItem(getChatCacheKey(reportId), JSON.stringify(merged));
        } else {
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
  }, [reportId, language]);

  useEffect(() => {
    if (!reportId || messages.length === 0) return;
    localStorage.setItem(getChatCacheKey(reportId), JSON.stringify(messages));
  }, [messages, reportId]);

  // Scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text) => {
    if (!text.trim() || isLoading || !reportId) return;

    const userMessage = { id: Date.now().toString(), sender: 'user', text };
    setMessages(prev => [...prev, userMessage]);
    setInputVal('');
    setIsLoading(true);

    try {
      const response = await api.chat.send(reportId, text);
      const aiResponse = { 
        id: (Date.now() + 1).toString(), 
        sender: 'ai', 
        text: response.reply 
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages(prev => [...prev, {
        id: 'err', sender: 'ai',
        text: language === 'ar' ? 'عذراً، حدث خطأ أثناء الاتصال بالخادم.' : 'Sorry, an error occurred while connecting to the engine.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFullReport = async () => {
    if (isReporting || !reportId) return;
    setIsReporting(true);
    setMessages(prev => [...prev, {
      id: 'fr-loading',
      sender: 'ai',
      text: language === 'ar' 
        ? '⏳ جارٍ إنشاء تقرير شامل متعدد الوكلاء... قد يستغرق هذا دقيقة أو أكثر.'
        : '⏳ Generating full multi-agent diagnostic report... This may take 1-2 minutes.'
    }]);
    try {
      const result = await api.diagnostics.fullReport(reportId);
      setMessages(prev => prev.filter(m => m.id !== 'fr-loading').concat({
        id: `fr-${Date.now()}`,
        sender: 'ai',
        text: result.explanation || (language === 'ar' ? 'لم يتم إنشاء التقرير.' : 'No report was generated.')
      }));
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== 'fr-loading').concat({
        id: 'fr-err',
        sender: 'ai',
        text: language === 'ar' ? 'فشل إنشاء التقرير الشامل. يرجى المحاولة مجدداً.' : 'Failed to generate full report. Please try again.'
      }));
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
          {isLoading && (
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
              disabled={!reportId || isLoading}
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
            disabled={!reportId || isLoading}
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
          <button className={styles.sendBtn} onClick={() => handleSend(inputVal)} disabled={!reportId || isLoading}>
            <Send size={20} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
