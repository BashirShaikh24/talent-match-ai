import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, single } from 'rxjs';
import { CandidateData, JobDescriptionData } from '../models';

@Injectable({ providedIn: 'root' })
export class TalentMatchService {
  private apiUrl = 'http://localhost:5000/api';
  public isModalOpen = signal({
    state: false,
    selectedData: null as CandidateData | JobDescriptionData | null,
    uploadedType: '',
  });

  constructor(private http: HttpClient) {}

  uploadResume(file: File, uploadType: string): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('uploadType', uploadType);

    return this.http.post(`${this.apiUrl}/upload-resume`, formData);
  }

  getCandidateList() {
    return this.http.get(`${this.apiUrl}/candidate_list`);
  }

  getMatchScore(cd_result: any, jd_result: any) {
    return this.http.post(`${this.apiUrl}/match-score-with-ai`, {
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
