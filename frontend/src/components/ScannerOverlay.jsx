import React, { useEffect, useState, useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { useNavigate } from 'react-router-dom';
import { Activity, Cpu, Zap, CheckCircle2, Bluetooth, Usb } from 'lucide-react';
import styles from './ScannerOverlay.module.css';

export default function ScannerOverlay() {
  const { isScanning, setIsScanning, language } = useContext(AppContext);
  const navigate = useNavigate();
  const [step, setStep] = useState('prompt'); // 'prompt', 'pairing', 'scanning'
  const [phase, setPhase] = useState(0);

  const phases = [
    { icon: Activity, textEn: "Initializing OBD-II Protocol...", textAr: "تهيئة بروتوكول OBD-II..." },
    { icon: Cpu, textEn: "Interfacing with Engine Control Unit...", textAr: "قراءة وحدة التحكم بالمحرك..." },
    { icon: Zap, textEn: "Analyzing Electrical Subsystems...", textAr: "تحليل الأنظمة الكهربائية..." },
    { icon: CheckCircle2, textEn: "Compiling Diagnostic Report...", textAr: "إعداد التقرير الشامل..." }
  ];

  useEffect(() => {
    if (isScanning) {
      setStep('prompt');
      setPhase(0);
    }
  }, [isScanning]);

  useEffect(() => {
    if (!isScanning) return;
    
    if (step === 'pairing') {
      const timer = setTimeout(() => {
        setStep('scanning');
      }, 3500);
      return () => clearTimeout(timer);
    }
    
    if (step === 'scanning') {
      const interval = setInterval(() => {
        setPhase(p => {
          if (p >= phases.length - 1) {
            clearInterval(interval);
            setTimeout(() => {
              setIsScanning(false);
              navigate('/diagnostics');
            }, 1000);
            return p;
          }
          return p + 1;
        });
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [step, isScanning, navigate, setIsScanning]);

  if (!isScanning) return null;

  return (
    <AnimatePresence>
      <motion.div className={styles.overlay} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
        <button className={styles.closeBtn} onClick={() => setIsScanning(false)}>✕</button>

        {step === 'prompt' && (
          <motion.div key="prompt" className={styles.promptBox} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
            <div className={styles.promptIconBlock}>
               <Usb size={40} className={styles.usbIcon} />
            </div>
            <h2>{language === 'ar' ? 'توصيل جهاز الفحص' : 'Connect OBD-II Device'}</h2>
            <p>{language === 'ar' ? 'يرجى التأكد من توصيل قطعة الفحص بمقبس OBD-II في مركبتك وتفعيل البلوتوث.' : 'Ensure your diagnostic dongle is securely plugged into your vehicle\'s OBD-II port under the dashboard.'}</p>
            <button className={`${styles.actionBtn} btn-primary`} onClick={() => setStep('pairing')}>
               <Bluetooth size={20} />
               {language === 'ar' ? 'البحث عن أجهزة' : 'Scan for Devices'}
            </button>
          </motion.div>
        )}

        {step === 'pairing' && (
          <motion.div key="pairing" className={styles.pairingBox} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className={styles.pairingIconWrapper}>
               <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} className={styles.pairingRing} />
               <Bluetooth size={40} className={styles.btIcon} />
            </div>
            <h3>{language === 'ar' ? 'جاري البحث عن ELM327...' : 'Discovering ELM327 Adapter...'}</h3>
          </motion.div>
        )}

        {step === 'scanning' && (
          <motion.div key="scanning" className={styles.scanningWrap} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className={styles.scanBox}>
               <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} className={styles.radar} />
               <div className={styles.radarCore}>
                 {React.createElement(phases[phase].icon, { size: 48, className: styles.radarIcon })}
               </div>
            </div>

            <div className={styles.statusList}>
              {phases.map((p, i) => (
                <motion.div key={i} className={`${styles.statusItem} ${i === phase ? styles.active : ''} ${i < phase ? styles.completed : ''}`} initial={{ opacity: 0, x: -20 }} animate={{ opacity: i <= phase ? 1 : 0.3, x: 0 }}>
                  <div className={styles.dot} />
                  <span>{language === 'ar' ? p.textAr : p.textEn}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
