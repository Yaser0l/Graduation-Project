export const mockData = {
  vehicles: [
    {
      id: "v1", make: "Toyota", model: "Camry", year: 2018, mileage: 85400,
      healthStatus: "Drive with Caution", healthScore: 78, healthColor: "yellow"
    }
  ],
  brands: ["Toyota", "Hyundai", "Ford", "Chevrolet", "Nissan"],
  models: {
    "Toyota": ["Camry", "Corolla", "Land Cruiser", "Yaris"],
    "Hyundai": ["Elantra", "Sonata", "Tucson", "Accent"]
  },
  diagnostics: {
    scanDate: "2026-04-03T06:05:00Z",
    overallSeverity: "Medium",
    categories: [
      {
        id: "engine", titleEn: "Engine & Powertrain", titleAr: "المحرك وناقل الحركة",
        issues: [
          {
            code: "P0171", severity: "High", isResolved: false,
            descEn: "System Too Lean (Bank 1)", descAr: "نظام الوقود ضعيف (الضفة 1)",
            plainEn: "The engine is getting too much air and not enough fuel. Check for vacuum leaks or a dirty mass airflow sensor.",
            plainAr: "المحرك يحصل على هواء زائد ووقود غير كافٍ. قد يكون هناك تسريب هواء أو اتساخ في حساس الهواء.",
            cost: { parts: 350, labor: 150, total: 500, currency: "SAR" }
          },
          {
            code: "P0300", severity: "Medium", isResolved: true,
            descEn: "Random/Multiple Cylinder Misfire Detected", descAr: "اكتشاف خلل في إشعال الأسطوانات",
            plainEn: "Historical misfire detected, previously resolved via spark plug replacement.",
            plainAr: "تم اكتشاف خلل إشعال سابق، وتم حله بتغيير شمعات الاحتراق.",
            cost: { parts: 0, labor: 0, total: 0, currency: "SAR" }
          }
        ]
      },
      {
        id: "electrical", titleEn: "Electrical System", titleAr: "النظام الكهربائي",
        issues: [
          {
            code: "U0100", severity: "Low", isResolved: false,
            descEn: "Lost Communication with ECM/PCM", descAr: "فقدان الاتصال مع وحدة التحكم",
            plainEn: "Intermittent connection drop with the main computer. Often a loose battery terminal or wiring issue.",
            plainAr: "انقطاع متقطع في الاتصال بالكمبيوتر الرئيسي. غالبًا بسبب تراخي أطراف البطارية.",
            cost: { parts: 0, labor: 100, total: 100, currency: "SAR" }
          }
        ]
      }
    ]
  },
  maintenanceTimeline: [
    {
      id: "m1", category: "Fluids", titleEn: "Synthetic Oil Change", titleAr: "تغيير زيت تخليقي",
      dueInKm: -120, progress: 100, status: "overdue", urgency: "High"
    },
    {
      id: "m2", category: "Brakes", titleEn: "Front Brake Pads", titleAr: "أقمشة الفرامل الأمامية",
      dueInKm: 1500, progress: 85, status: "due-soon", urgency: "Medium"
    },
    {
      id: "m3", category: "Engine", titleEn: "Spark Plugs", titleAr: "شمعات الاحتراق (بواجي)",
      dueInKm: 12000, progress: 40, status: "healthy", urgency: "Low"
    },
    {
      id: "m4", category: "Filters", titleEn: "Cabin Air Filter", titleAr: "فلتر هواء المقصورة",
      dueInKm: 5000, progress: 60, status: "healthy", urgency: "Low"
    }
  ],
  chatQuickReplies: [
    { id: "q1", action: "details_P0171", textEn: "Explain P0171 simply.", textAr: "اشرح عطل P0171 ببساطة." },
    { id: "q2", action: "DIY_P0171", textEn: "Can I fix P0171 myself?", textAr: "هل يمكنني إصلاحه بنفسي؟" },
    { id: "q3", action: "cost_U0100", textEn: "Is U0100 expensive?", textAr: "هل إصلاح U0100 مكلف؟" },
  ]
};
