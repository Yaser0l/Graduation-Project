import React, { useContext, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import { AppContext } from '../store/AppContext';
import { api } from '../services/api';
import { Send, Zap, MessageCircle } from 'lucide-react';
import styles from './Chat.module.css';

export default function Chat() {
  const { mockData, language } = useContext(AppContext);
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const reportId = searchParams.get('reportId');

  const [messages, setMessages] = useState([]);
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);

  // Load History
  useEffect(() => {
    const loadHistory = async () => {
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
        const historyData = await api.chat.history(reportId);
        if (historyData.messages && historyData.messages.length > 0) {
          const mapped = historyData.messages.map((m, idx) => ({
            id: `h-${idx}`,
            sender: m.role === 'user' ? 'user' : 'ai',
            text: m.content
          }));
          setMessages(mapped);
        } else {
          setMessages([{
            id: 'initial',
            sender: 'ai',
            text: language === 'ar' 
              ? 'الأنظمة متصلة. أنا مستعد لمناقشة التقرير التشخيصي معك.'
              : 'Systems interfaced. I am ready to discuss the diagnostic report with you.'
          }]);
        }
      } catch (err) {
        console.error("Failed to load history:", err);
      }
    };
    loadHistory();
  }, [reportId, language]);

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

  const chips = mockData.chatQuickReplies;

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
              <div className={`${styles.bubble} ${styles[msg.sender]}`}>{msg.text}</div>
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
          <button className={styles.sendBtn} onClick={() => handleSend(inputVal)} disabled={!reportId || isLoading}>
            <Send size={20} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
