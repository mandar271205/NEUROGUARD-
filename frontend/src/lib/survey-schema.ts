export type SurveyQuestion = {
  key: string;
  label: string;
  min: number;
  max: number;
};

export const surveyQuestions: SurveyQuestion[] = [
  { key: "anxiety_level", label: "Anxiety level", min: 0, max: 10 },
  { key: "self_esteem", label: "Self esteem", min: 0, max: 10 },
  { key: "mental_health_history", label: "Mental health history", min: 0, max: 1 },
  { key: "depression", label: "Depression", min: 0, max: 10 },
  { key: "headache", label: "Headache", min: 0, max: 10 },
  { key: "blood_pressure", label: "Blood pressure", min: 0, max: 10 },
  { key: "sleep_quality", label: "Sleep quality", min: 0, max: 10 },
  { key: "breathing_problem", label: "Breathing problem", min: 0, max: 10 },
  { key: "noise_level", label: "Noise level", min: 0, max: 10 },
  { key: "living_conditions", label: "Living conditions", min: 0, max: 10 },
  { key: "safety", label: "Safety", min: 0, max: 10 },
  { key: "basic_needs", label: "Basic needs", min: 0, max: 10 },
  { key: "academic_performance", label: "Academic performance", min: 0, max: 10 },
  { key: "study_load", label: "Study load", min: 0, max: 10 },
  {
    key: "teacher_student_relationship",
    label: "Teacher-student relationship",
    min: 0,
    max: 10
  },
  { key: "future_career_concerns", label: "Future career concerns", min: 0, max: 10 },
  { key: "social_support", label: "Social support", min: 0, max: 10 },
  { key: "peer_pressure", label: "Peer pressure", min: 0, max: 10 },
  {
    key: "extracurricular_activities",
    label: "Extracurricular activities",
    min: 0,
    max: 10
  },
  { key: "bullying", label: "Bullying", min: 0, max: 10 }
];
