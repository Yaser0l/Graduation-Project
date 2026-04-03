import React, { useState, useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { AppContext } from '../store/AppContext';
import { Mail, Lock, LogIn, UserPlus } from 'lucide-react';
import styles from './Welcome.module.css';

export default function Welcome() {
  const [isLogin, setIsLogin] = useState(false);
  const { language } = useContext(AppContext);
  const navigate = useNavigate();

  const handleAuth = (e) => {
    e.preventDefault();
    /* ==============================================================
     * [BACKEND INTEGRATION: AUTHENTICATION]
     * Endpoint: POST /api/auth/login OR POST /api/auth/register
     * Payload: { email, password }
     * Action: Store `access_token` JWT in localStorage here.
     * ============================================================== */
    navigate('/onboarding');
  };

  return (
    <motion.div className={styles.container} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className={styles.hero}>
        <motion.h1 initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className={styles.logo}>
          Vehicle AI
        </motion.h1>
        <p className={styles.subtitle}>
          {language === 'ar' 
            ? 'منصتك المتقدمة لتشخيص الأعطال وتتبع صيانة مركبتك بذكاء.' 
            : 'The premium intelligence engine for advanced vehicle diagnostics and maintenance tracking.'}
        </p>
      </div>

      <motion.div className={styles.authBox} initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className={styles.authTabs}>
          <div className={`${styles.tab} ${!isLogin ? styles.active : ''}`} onClick={() => setIsLogin(false)}>
            {language === 'ar' ? 'حساب جديد' : 'Sign Up'}
          </div>
          <div className={`${styles.tab} ${isLogin ? styles.active : ''}`} onClick={() => setIsLogin(true)}>
            {language === 'ar' ? 'تسجيل الدخول' : 'Login'}
          </div>
        </div>

        <form className={styles.form} onSubmit={handleAuth}>
          <div className={styles.inputGroup}>
            <Mail size={18} className={styles.icon} />
            <input type="email" placeholder={language === 'ar' ? 'البريد الإلكتروني' : 'Email Address'} className={styles.input} required />
          </div>
          <div className={styles.inputGroup}>
            <Lock size={18} className={styles.icon} />
            <input type="password" placeholder={language === 'ar' ? 'كلمة المرور' : 'Password'} className={styles.input} required />
          </div>
          
          <button type="submit" className={styles.submitBtn}>
            {isLogin ? (
              <><LogIn size={18} /> {language === 'ar' ? 'دخول' : 'Authenticate'}</>
            ) : (
              <><UserPlus size={18} /> {language === 'ar' ? 'إنشاء حساب' : 'Create Context'}</>
            )}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}
