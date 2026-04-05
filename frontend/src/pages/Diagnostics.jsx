import React, { useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { useNavigate } from 'react-router-dom';
import { Tag, ChevronDown, MessageSquareText, Calendar, AlertCircle, CheckCircle2 } from 'lucide-react';
import styles from './Diagnostics.module.css';

export default function Diagnostics() {
  const { diagnostics, language, resolveDiagnostic } = useContext(AppContext);
  const [expandedReport, setExpandedReport] = useState(diagnostics?.[0]?.id || null);
  const [resolvingReportId, setResolvingReportId] = useState(null);
  const navigate = useNavigate();

  const containerVars = { 
    hidden: { opacity: 0 }, 
    show: { opacity: 1, transition: { staggerChildren: 0.1 } } 
  };
  const itemVars = { 
    hidden: { y: 20, opacity: 0 }, 
    show: { y: 0, opacity: 1 } 
  };

  if (!diagnostics || diagnostics.length === 0) {
    return (
      <div className={styles.emptyState}>
        <AlertCircle size={48} />
        <h2>{language === 'ar' ? 'لا توجد تقارير حالياً' : 'No Reports Available'}</h2>
        <p>{language === 'ar' ? 'قم بإجراء فحص للمركبة للحصول على نتائج.' : 'Run a vehicle scan to see diagnostic results.'}</p>
      </div>
    );
  }

  const handleResolve = async (reportId) => {
    if (resolvingReportId) return;
    setResolvingReportId(reportId);
    try {
      await resolveDiagnostic(reportId);
    } catch (err) {
      console.error('Failed to resolve diagnostic:', err);
    } finally {
      setResolvingReportId(null);
    }
  };

  return (
    <motion.div className={styles.container} variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}>
      <motion.div variants={itemVars} className={styles.header}>
        <h1 className={styles.title}>{language === 'ar' ? 'سجل الفحص الذكي' : 'Diagnostic History'}</h1>
      </motion.div>

      {diagnostics.map((report) => (
        <motion.div variants={itemVars} key={report.id} className={`glass-panel ${styles.categoryGroup}`}>
          <div className={styles.catHeader} onClick={() => setExpandedReport(expandedReport === report.id ? null : report.id)}>
            <div className={styles.catTitle}>
              <Calendar size={18} />
              <span>{new Date(report.created_at).toLocaleDateString(language === 'ar' ? 'ar-SA' : 'en-US', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
              <div className={styles.dtcCounts}>
                <span className={styles.dtcBadge}>{report.dtc_codes.length} {language === 'ar' ? 'أكواد' : 'Codes'}</span>
              </div>
            </div>
            <ChevronDown className={`${styles.chevron} ${expandedReport === report.id ? styles.rotated : ''}`} />
          </div>

          <AnimatePresence>
            {expandedReport === report.id && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }} 
                animate={{ height: 'auto', opacity: 1 }} 
                exit={{ height: 0, opacity: 0 }}
                className={styles.issueList}
              >
                <div className={styles.issueCard}>
                  <div className={styles.issueTop}>
                    <div className={styles.dtcChips}>
                      {report.dtc_codes.map(code => (
                        <div key={code} className={styles.dtcChipItem}>
                          <span className={styles.codeTag}>{code}</span>
                          {!report.resolved && (
                            <button
                              type="button"
                              className={styles.resolveChipBtn}
                              onClick={() => handleResolve(report.id)}
                              disabled={resolvingReportId === report.id}
                            >
                              {resolvingReportId === report.id
                                ? (language === 'ar' ? 'جارٍ...' : '...')
                                : (language === 'ar' ? 'حل' : 'Resolve')}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    {report.resolved ? (
                      <span className={`${styles.severityTag} ${styles.resolvedTag}`}>
                        {language === 'ar' ? 'تم الحل' : 'Resolved'}
                      </span>
                    ) : (
                      <span className={`${styles.severityTag} ${styles[report.urgency?.toLowerCase() || 'medium']}`}>
                        {report.urgency || 'Medium'}
                      </span>
                    )}
                  </div>

                  <div className={styles.plainBox}>
                    <h3>{language === 'ar' ? 'تحليل الذكاء الاصطناعي' : 'AI Analysis'}</h3>
                    <p>{report.llm_explanation || (language === 'ar' ? 'جاري تحليل البيانات...' : 'Analyzing diagnostic data...')}</p>
                  </div>

                  <div className={styles.issueFooter}>
                    <div className={styles.costBadge}>
                      <Tag size={16} color="var(--accent-primary)" />
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <small>{language === 'ar' ? 'التكلفة التقديرية' : 'Est. Repair Cost'}</small>
                        <span>
                          {report.estimated_cost_min || 0} - {report.estimated_cost_max || 0} {language === 'ar' ? 'ريال' : 'SAR'}
                        </span>
                      </div>
                    </div>

                    <div className={styles.actionsRow}>
                      {!report.resolved && (
                        <button
                          type="button"
                          className={styles.resolveBtn}
                          onClick={() => handleResolve(report.id)}
                          disabled={resolvingReportId === report.id}
                        >
                          <CheckCircle2 size={16} />
                          <span>
                            {resolvingReportId === report.id
                              ? (language === 'ar' ? 'جارٍ الإغلاق...' : 'Resolving...')
                              : (language === 'ar' ? 'إغلاق المشكلة' : 'Resolve Issue')}
                          </span>
                        </button>
                      )}
                      <button className={styles.askAiBtn} onClick={() => navigate(`/chat?reportId=${report.id}`)}>
                        <MessageSquareText size={16}/>
                        <span>{language === 'ar' ? 'مناقشة هذا التقرير' : 'Discuss Report'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </motion.div>
  );
}
