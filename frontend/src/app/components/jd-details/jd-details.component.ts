import { Component, EventEmitter, Input, Output, ViewEncapsulation } from '@angular/core';
import { JobDescriptionData, UploadType } from '../../models';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-jd-details',
  templateUrl: './jd-details.component.html',
  styleUrl: './jd-details.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class JdDetailsComponent {
  @Input() jobDescription: JobDescriptionData | null = null;

  @Output() closeModal = new EventEmitter<boolean>();

  constructor(public talentMatchService: TalentMatchService) {}

  downloadResume(fileName: string) {
    this.talentMatchService.downloadUploadedFile(fileName, UploadType.JD).subscribe((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = fileName;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  closeDetailsModal() {
    this.talentMatchService.isModalOpen.set({ state: false, selectedData: null, uploadedType: '' });
  }
}
