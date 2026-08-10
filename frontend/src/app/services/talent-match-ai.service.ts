import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CandidateData,
  CandidateMatchResult,
  JobDescriptionData,
  UploadResumeResponse,
} from '../models';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class TalentMatchService {
  private apiUrl = environment.apiUrl;
  public isModalOpen = signal({
    state: false,
    selectedData: null as CandidateData | JobDescriptionData | null,
    uploadedType: '',
  });
  public isCandidateEvaluated = signal<CandidateData | null>(null);

  constructor(private http: HttpClient) {}

  uploadResume(
    file: File,
    uploadType: string,
  ): Observable<{
    filename: string;
    message: string;
    results: CandidateData | JobDescriptionData;
    uploadType: string;
  }> {
    const formData = new FormData();

    formData.append('file', file);
    formData.append('uploadType', uploadType);

    return this.http.post<UploadResumeResponse>(`${this.apiUrl}/upload-resume`, formData);
  }

  getCandidateList() {
    return this.http.get(`${this.apiUrl}/candidate_list`);
  }

  getMatchScore(
    cd_result: CandidateData,
    jd_result: JobDescriptionData,
  ): Observable<CandidateMatchResult> {
    return this.http.post<CandidateMatchResult>(`${this.apiUrl}/match-score-with-ai`, {
      cd_result,
      jd_result,
    });
  }

  downloadUploadedFile(fileName: string, uploadType: string): Observable<Blob> {
    const formData = new FormData();
    formData.append('uploadType', uploadType);

    return this.http.get(`${this.apiUrl}/download-uploaded-file/${fileName}`, {
      params: { uploadType },
      responseType: 'blob',
    });
  }

  removeTimestampFromFilename(filename: string): string {
    return filename?.replace(/_\d{14}(?=\.\w+$)/, '') || '';
  }
}
