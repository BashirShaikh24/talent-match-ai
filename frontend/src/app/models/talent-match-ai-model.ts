export interface CandidateData {
  id?: string | number;
  name?: string;
  skills?: string[];
  role?: string;
  summary?: string;
  responsibilities?: string[];
  match_percentage?: number;
  email?: string;
  contact_no?: number;
  isMatching?: boolean;
  filename?: string;
  years_of_experience?: number;
  location?: string;
}

export interface JobDescriptionData {
  filename?: string;
  title?: string;
  required_skills?: string[];
  nice_to_have_skills?: string[];
  responsibilities?: string[];
  min_years_experience?: number;
  max_years_experience?: number;
  summary?: string;
}

export enum UploadType {
  JD = 'JD',
  CD = 'CD',
}
