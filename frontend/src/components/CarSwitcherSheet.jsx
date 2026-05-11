import React, { useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { LanguageContext, VehicleContext } from '../store/AppContext';
import { Plus, CarFront, CheckCircle2, Trash2, Loader2 } from 'lucide-react';
import styles from './CarSwitcherSheet.module.css';

export default function CarSwitcherSheet({ isOpen, onClose }) {
  const { vehicles, activeVehicle, setActiveVehicle, removeVehicle } = useContext(VehicleContext);
  const { language } = useContext(LanguageContext);
  const [deletingVehicleId, setDeletingVehicleId] = useState(null);
  const navigate = useNavigate();

  const handleSelect = (vehicle) => {
    setActiveVehicle(vehicle);
    onClose();
  };

  const handleAddVehicle = () => {
    onClose();
    navigate('/onboarding');
  };

  const handleRemoveVehicle = async (vehicle, e) => {
    e.stopPropagation();
    if (deletingVehicleId) return;

    const vehicleLabel = `${vehicle.year} ${vehicle.make} ${vehicle.model}`;
    const confirmText = language === 'ar'
      ? `هل أنت متأكد من حذف المركبة ${vehicleLabel}؟ لا يمكن التراجع عن هذا الإجراء.`
      : `Are you sure you want to remove ${vehicleLabel}? This action cannot be undone.`;

    if (!window.confirm(confirmText)) return;

    setDeletingVehicleId(vehicle.id);
    try {
      await removeVehicle(vehicle.id);
    } catch (error) {
      console.error('Failed to remove vehicle:', error);
      const message = language === 'ar'
        ? 'تعذر حذف المركبة. حاول مرة أخرى.'
        : 'Failed to remove vehicle. Please try again.';
      window.alert(message);
    } finally {
      setDeletingVehicleId(null);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className={styles.backdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Sheet Panel */}
          <motion.div
            className={styles.sheet}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 350, damping: 35 }}
          >
            {/* Handle */}
            <div className={styles.handle} />

            <h2 className={styles.title}>
              {language === 'ar' ? 'مركباتي' : 'My Vehicles'}
            </h2>

            {/* Vehicle List */}
            <div className={styles.vehicleList}>
              {vehicles.length === 0 ? (
                <div className={styles.emptyVehicles}>
                  <CarFront size={36} className={styles.emptyIcon} />
                  <p>{language === 'ar' ? 'لا توجد مركبات مضافة.' : 'No vehicles added yet.'}</p>
                </div>
              ) : (
                vehicles.map((vehicle) => {
                  const isActive = activeVehicle?.id === vehicle.id;
                  const isDeleting = deletingVehicleId === vehicle.id;
                  return (
                    <div key={vehicle.id} className={styles.vehicleRow}>
                      <button
                        className={`${styles.vehicleCard} ${isActive ? styles.activeCard : ''}`}
                        onClick={() => handleSelect(vehicle)}
                        disabled={isDeleting}
                      >
                        <div className={styles.vehicleIconWrap}>
                          <CarFront size={28} className={isActive ? styles.activeCarIcon : styles.carIcon} />
                        </div>
                        <div className={styles.vehicleInfo}>
                          <span className={styles.vehicleName}>
                            {vehicle.year} {vehicle.make} {vehicle.model}
                          </span>
                          {vehicle.vin && (
                            <span className={styles.vehicleVin}>VIN: {vehicle.vin}</span>
                          )}
                          {vehicle.mileage && (
                            <span className={styles.vehicleMileage}>
                              {vehicle.mileage.toLocaleString()} km
                            </span>
                          )}
                        </div>
                        {isActive && (
                          <CheckCircle2 size={22} className={styles.checkIcon} />
                        )}
                      </button>

                      <button
                        type="button"
                        className={styles.removeVehicleBtn}
                        onClick={(e) => handleRemoveVehicle(vehicle, e)}
                        disabled={isDeleting}
                        title={language === 'ar' ? 'حذف المركبة' : 'Remove vehicle'}
                        aria-label={language === 'ar' ? 'حذف المركبة' : 'Remove vehicle'}
                      >
                        {isDeleting ? <Loader2 size={16} className={styles.spinner} /> : <Trash2 size={16} />}
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            {/* Add Vehicle Button */}
            <button className={styles.addVehicleBtn} onClick={handleAddVehicle}>
              <Plus size={20} />
              <span>{language === 'ar' ? 'إضافة مركبة جديدة' : 'Add New Vehicle'}</span>
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
