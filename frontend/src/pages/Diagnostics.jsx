import React, { useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { useNavigate } from 'react-router-dom';
import { Tag, ChevronDown, MessageSquareText } from 'lucide-react';
import styles from './Diagnostics.module.css';

export default function Diagnostics() {
  const { diagnostics, language } = useContext(AppContext);
  const [expandedCat, setExpandedCat] = useState(diagnostics.categories[0]?.id);
  const navigate = useNavigate();

  const containerVars = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
  const itemVars = { hidden: { y: 20, opacity: 0 }, show: { y: 0, opacity: 1 } };

  return (
    <motion.div className={styles.container} variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}>
      <motion.div variants={itemVars} className={styles.header}>
        <h1 className={styles.title}>{language === 'ar' ? 'التقرير الشامل' : 'System Scan'}</h1>
      </motion.div>

      {diagnostics.categories.map(cat => (
        <motion.div variants={itemVars} key={cat.id} className={`glass-panel ${styles.categoryGroup}`}>
          <div className={styles.catHeader} onClick={() => setExpandedCat(expandedCat === cat.id ? null : cat.id)}>
            <h2>{language === 'ar' ? cat.titleAr : cat.titleEn}</h2>
            <ChevronDown className={`${styles.chevron} ${expandedCat === cat.id ? styles.rotated : ''}`} />
          </div>

          <AnimatePresence>
            {expandedCat === cat.id && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }} 
                animate={{ height: 'auto', opacity: 1 }} 
                exit={{ height: 0, opacity: 0 }}
                className={styles.issueList}
              >
                {cat.issues.map((issue, idx) => (
                  <div key={idx} className={styles.issueCard}>
                    <div className={styles.issueTop}>
                      <span className={styles.codeTag}>{issue.code}</span>
                      <span className={`${styles.severityTag} ${styles[issue.severity.toLowerCase()]}`}>
                        {issue.severity}
                      </span>
                    </div>
                    <h3>{language === 'ar' ? issue.descAr : issue.descEn}</h3>
                    <div className={styles.plainBox}>
                      <p>{language === 'ar' ? issue.plainAr : issue.plainEn}</p>
                    </div>
                    
                    <div className={styles.issueFooter}>
                      {issue.cost.parts > 0 ? (
                        <div className={styles.costBadge}>
                          <Tag size={16} color="var(--accent-primary)" />
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            <small>{language === 'ar' ? 'سعر القطعة' : 'Est. Parts'}</small>
                            <span>{issue.cost.parts} {issue.cost.currency}</span>
                          </div>
                        </div>
                      ) : <div />}

                      <button className={styles.askAiBtn} onClick={() => navigate('/chat')}>
                         <MessageSquareText size={16}/>
                         <span>{language === 'ar' ? 'اسأل الذكاء الاصطناعي عن هذا العطل' : 'Ask AI about this'}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </motion.div>
  );
}
