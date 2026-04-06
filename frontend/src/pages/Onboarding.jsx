import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { Car, Settings2, Fingerprint, GaugeCircle } from 'lucide-react';
import styles from './Onboarding.module.css';

export default function Onboarding() {
  const navigate = useNavigate();
  const { language, addVehicle } = useContext(AppContext);

  const [make, setMake]       = useState('');
  const [model, setModel]     = useState('');
  const [year, setYear]       = useState('');
  const [vin, setVin]         = useState('');
  const [mileage, setMileage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]     = useState(null);

  const ar = language === 'ar';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!make.trim() || !model.trim() || !year.trim() || !vin.trim() || vin.trim().length !== 17) {
      setError(ar ? 'يرجى تعبئة جميع الحقول المطلوبة بما في ذلك رقم الهيكل (١٧ حرف/رقم).' : 'Please fill in all required fields including the 17-character VIN.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await addVehicle({
        vin:     vin.trim().toUpperCase(),
        make:    make.trim(),
        model:   model.trim(),
        year:    parseInt(year, 10),
        mileage: parseInt(mileage, 10) || 0,
      });
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to register vehicle:', err);
      setError(err.message || (ar ? 'فشل الحفظ. حاول مرة أخرى.' : 'Failed to save. Please try again.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className={styles.container}
    >
      <div className={styles.header}>
        <motion.div
          initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className={styles.logo}
        >
          Vehicle AI
        </motion.div>
        <p className={styles.subtitle}>
          {ar ? 'أدخل بيانات مركبتك' : 'Register Your Vehicle'}
        </p>
      </div>

      <motion.form
        initial={{ y: 24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className={styles.formBox}
        onSubmit={handleSubmit}
      >
        {error && <div className={styles.errorBanner}>{error}</div>}

        <div className={styles.field}>
          <label htmlFor="make" className={styles.label}>
            <Car size={16} />
            {ar ? 'الشركة المصنّعة' : 'Manufacturer'}
            <span className={styles.required}>*</span>
          </label>
          <input
            id="make"
            type="text"
            className={styles.input}
            placeholder={ar ? 'مثال: Toyota' : 'e.g. Toyota'}
            value={make}
            onChange={e => setMake(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="model" className={styles.label}>
            <Settings2 size={16} />
            {ar ? 'الطراز' : 'Model / Type'}
            <span className={styles.required}>*</span>
          </label>
          <input
            id="model"
            type="text"
            className={styles.input}
            placeholder={ar ? 'مثال: Camry' : 'e.g. Camry'}
            value={model}
            onChange={e => setModel(e.target.value)}
            required
          />
        </div>

        <div className={styles.row}>
          <div className={styles.field}>
            <label htmlFor="year" className={styles.label}>
              {ar ? 'سنة الصنع' : 'Year'}
              <span className={styles.required}>*</span>
            </label>
            <input
              id="year"
              type="number"
              className={styles.input}
              placeholder={ar ? 'مثال: 2021' : 'e.g. 2021'}
              value={year}
              onChange={e => setYear(e.target.value)}
              min={1980}
              max={2026}
              required
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="mileage" className={styles.label}>
              <GaugeCircle size={16} />
              {ar ? 'الممشى (كم)' : 'Mileage (km)'}
            </label>
            <input
              id="mileage"
              type="number"
              className={styles.input}
              placeholder={ar ? 'مثال: 85000' : 'e.g. 85000'}
              value={mileage}
              onChange={e => setMileage(e.target.value)}
              min={0}
            />
          </div>
        </div>

        <div className={styles.field}>
          <label htmlFor="vin" className={styles.label}>
            <Fingerprint size={16} />
            {ar ? 'رقم الهيكل VIN' : 'VIN Number'}
            <span className={styles.required}>*</span>
          </label>
          <input
            id="vin"
            type="text"
            className={styles.input}
            placeholder="e.g. 1HGCM82633A004352"
            value={vin}
            onChange={e => setVin(e.target.value.toUpperCase())}
            minLength={17}
            maxLength={17}
            required
          />
        </div>

        <button
          type="submit"
          className={`btn-primary ${styles.submitBtn}`}
          disabled={isLoading}
        >
          {isLoading
            ? (ar ? 'جاري الحفظ...' : 'Saving...')
            : (ar ? 'تسجيل المركبة' : 'Register Vehicle')}
        </button>
      </motion.form>
    </motion.div>
  );
}
