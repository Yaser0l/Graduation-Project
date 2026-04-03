import React, { useState, useContext } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { AppContext } from '../store/AppContext';
import { Mail, Lock, LogIn, UserPlus, User } from 'lucide-react';
import styles from './Welcome.module.css';

export default function Welcome() {
  const [isLogin, setIsLogin] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState(null);

  const { language, login, register } = useContext(AppContext);
  const navigate = useNavigate();

  const handleAuth = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setLocalError(null);
    try {
      if (isLogin) {
        await login(email, password);
        navigate('/dashboard');
      } else {
        await register(name || email.split('@')[0], email, password);
        navigate('/onboarding');
      }
    } catch (err) {
      console.error("Auth error:", err);
      setLocalError(err.message || "Authentication failed");
    } finally {
      setIsLoading(false);
    }
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
          <div className={`${styles.tab} ${!isLogin ? styles.active : ''}`} onClick={() => { setIsLogin(false); setLocalError(null); }}>
            {language === 'ar' ? 'حساب جديد' : 'Sign Up'}
          </div>
          <div className={`${styles.tab} ${isLogin ? styles.active : ''}`} onClick={() => { setIsLogin(true); setLocalError(null); }}>
            {language === 'ar' ? 'تسجيل الدخول' : 'Login'}
          </div>
        </div>

        <form className={styles.form} onSubmit={handleAuth}>
          {localError && <div className={styles.errorMessage}>{localError}</div>}
          
          {!isLogin && (
            <div className={styles.inputGroup}>
              <User size={18} className={styles.icon} />
              <input 
                type="text" 
                placeholder={language === 'ar' ? 'الاسم بالكامل' : 'Full Name'} 
                className={styles.input} 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required 
              />
            </div>
          )}

          <div className={styles.inputGroup}>
            <Mail size={18} className={styles.icon} />
            <input 
              type="email" 
              placeholder={language === 'ar' ? 'البريد الإلكتروني' : 'Email Address'} 
              className={styles.input} 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
            />
          </div>
          <div className={styles.inputGroup}>
            <Lock size={18} className={styles.icon} />
            <input 
              type="password" 
              placeholder={language === 'ar' ? 'كلمة المرور' : 'Password'} 
              className={styles.input} 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>
          
          <button type="submit" className={styles.submitBtn} disabled={isLoading}>
            {isLoading ? (
              <span>{language === 'ar' ? 'جاري التحميل...' : 'Please Wait...'}</span>
            ) : (
              isLogin ? (
                <><LogIn size={18} /> {language === 'ar' ? 'دخول' : 'Authenticate'}</>
              ) : (
                <><UserPlus size={18} /> {language === 'ar' ? 'إنشاء حساب' : 'Create Context'}</>
              )
            )}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}
