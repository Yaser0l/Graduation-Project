import React, { useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { Send, Zap } from 'lucide-react';
import styles from './Chat.module.css';

export default function Chat() {
  const { mockData, language } = useContext(AppContext);
  const [messages, setMessages] = useState([
    {
      id: 'm1',
      sender: 'ai',
      text: language === 'ar' 
        ? 'الأنظمة متصلة. كيف يمكنني مساعدتك اليوم؟'
        : 'Systems interfaced. How can I assist you with your vehicle today?'
    }
  ]);
  const [inputVal, setInputVal] = useState('');
  const chips = mockData.chatQuickReplies;

  const handleSend = (text) => {
    if(!text.trim()) return;
    setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'user', text }]);
    setInputVal('');
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now().toString(), sender: 'ai',
        text: language === 'ar' ? 'فهمت سؤالك. هذا نموذج تجريبي.' : 'Processing request. Please note this is mock data.'
      }]);
    }, 1000);
  };

  return (
    <motion.div className={styles.container} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className={styles.chatArea}>
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
        </AnimatePresence>
      </div>

      <div className={styles.interactionZone}>
        <div className={styles.chipsContainer}>
          {chips.map(chip => (
            <button key={chip.id} className={styles.chip} onClick={() => handleSend(language === 'ar' ? chip.textAr : chip.textEn)}>
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
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend(inputVal)}
          />
          <button className={styles.sendBtn} onClick={() => handleSend(inputVal)}>
            <Send size={20} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
