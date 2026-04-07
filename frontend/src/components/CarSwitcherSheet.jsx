import React, { useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { LanguageContext, VehicleContext } from '../store/AppContext';
import { Check, Plus, CarFront, CheckCircle2 } from 'lucide-react';
import styles from './CarSwitcherSheet.module.css';

export default function CarSwitcherSheet({ isOpen, onClose }) {
  const { vehicles, activeVehicle, setActiveVehicle } = useContext(VehicleContext);
  const { language } = useContext(LanguageContext);
  const navigate = useNavigate();

  const handleSelect = (vehicle) => {
    setActiveVehicle(vehicle);
    onClose();
  };

  const handleAddVehicle = () => {
    onClose();
    navigate('/onboarding');
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
                  return (
                    <button
                      key={vehicle.id}
                      className={`${styles.vehicleCard} ${isActive ? styles.activeCard : ''}`}
                      onClick={() => handleSelect(vehicle)}
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
