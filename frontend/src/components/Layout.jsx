import React, { useContext, useState, useMemo } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { LanguageContext, AuthContext, NotificationContext } from '../store/AppContext';
import { LogOut, X, Bell } from 'lucide-react';
import BottomNav from './BottomNav';
import CarSwitcherSheet from './CarSwitcherSheet';
import styles from './Layout.module.css';
import logo from '../assets/logo.png';

export default function Layout() {
  const { language, toggleLanguage } = useContext(LanguageContext);
  const { logout } = useContext(AuthContext);
  const {
    notifications,
    notificationLog,
    dismissNotification,
    markNotificationRead,
    markAllNotificationsRead,
    clearNotificationLog,
  } = useContext(NotificationContext);
  const [carsSheetOpen, setCarsSheetOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const navigate = useNavigate();

  const unreadCount = useMemo(
    () => notificationLog.filter((note) => !note.read).length,
    [notificationLog]
  );

  const toggleNotifications = () => {
    setNotificationsOpen((prev) => {
      const next = !prev;
      if (next) markAllNotificationsRead();
      return next;
    });
  };

  return (
    <div className={styles.layout}>
      {/* Top Header */}
      <header className={styles.header}>
        <div className={styles.leftSide}>
          <button className={styles.langToggle} onClick={toggleLanguage}>
            {language === 'en' ? 'عربي' : 'EN'}
          </button>
        </div>
        <div className={styles.brand} onClick={() => navigate('/dashboard')}>
          <img src={logo} alt="Logo" className={styles.logoImg} />
        </div>
        <div className={styles.rightSide}>
          <button
            type="button"
            className={styles.bellBtn}
            onClick={toggleNotifications}
            aria-label={language === 'ar' ? 'الإشعارات' : 'Notifications'}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className={styles.bellBadge}>{Math.min(unreadCount, 9)}</span>
            )}
          </button>
          <button type="button" className={styles.logoutBtn} onClick={logout}>
            <LogOut size={16} />
            <span className={styles.logoutText}>{language === 'ar' ? 'تسجيل الخروج' : 'Log Out'}</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className={styles.main}>
        <Outlet />
      </main>

      {notifications.length > 0 && (
        <div className={styles.toastStack}>
          {notifications.map((note) => (
            <div key={note.id} className={`${styles.toast} ${styles[note.type || 'info']}`}>
              <div className={styles.toastBody}>
                {note.title && <h4 className={styles.toastTitle}>{note.title}</h4>}
                {note.message && <p className={styles.toastMessage}>{note.message}</p>}
              </div>
              <button
                type="button"
                className={styles.toastClose}
                onClick={() => dismissNotification(note.id)}
                aria-label="Dismiss"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {notificationsOpen && (
        <div className={styles.notificationPanel}>
          <div className={styles.notificationHeader}>
            <div>
              <h4 className={styles.notificationTitle}>
                {language === 'ar' ? 'الإشعارات' : 'Notifications'}
              </h4>
              <p className={styles.notificationMeta}>
                {language === 'ar'
                  ? `${notificationLog.length} إشعار`
                  : `${notificationLog.length} notification${notificationLog.length === 1 ? '' : 's'}`}
              </p>
            </div>
            <div className={styles.notificationActions}>
              <button type="button" onClick={clearNotificationLog} className={styles.notificationLink}>
                {language === 'ar' ? 'مسح الكل' : 'Clear all'}
              </button>
              <button type="button" onClick={() => setNotificationsOpen(false)} className={styles.notificationLink}>
                {language === 'ar' ? 'إغلاق' : 'Close'}
              </button>
            </div>
          </div>

          <div className={styles.notificationList}>
            {notificationLog.length === 0 ? (
              <p className={styles.notificationEmpty}>
                {language === 'ar' ? 'لا توجد إشعارات حتى الآن.' : 'No notifications yet.'}
              </p>
            ) : (
              notificationLog.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  className={`${styles.notificationItem} ${note.read ? styles.read : styles.unread}`}
                  onClick={() => markNotificationRead(note.id)}
                >
                  <div className={styles.notificationItemBody}>
                    <div className={styles.notificationItemTitle}>{note.title || (language === 'ar' ? 'تنبيه' : 'Alert')}</div>
                    {note.message && <div className={styles.notificationItemMessage}>{note.message}</div>}
                    <div className={styles.notificationItemTime}>
                      {new Date(note.createdAt).toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Car Switcher Bottom Sheet */}
      <CarSwitcherSheet
        isOpen={carsSheetOpen}
        onClose={() => setCarsSheetOpen(false)}
      />

      {/* Fixed Bottom Navigation */}
      <BottomNav
        onCarsOpen={() => setCarsSheetOpen(true)}
        carsSheetOpen={carsSheetOpen}
      />
    </div>
  );
}
