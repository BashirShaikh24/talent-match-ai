import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  Output,
  ViewEncapsulation,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs/operators';
import { ToastrService } from 'ngx-toastr';
import { CandidateData, JobDescriptionData, UploadType } from '../../models';
import { UploadedJdDetailsComponent } from './uploaded-jd-details';
import { UploadedCdDetailsComponent } from './uploaded-cd-details';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-file-upload',
  templateUrl: './file-upload.component.html',
  styleUrl: './file-upload.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UploadedJdDetailsComponent, UploadedCdDetailsComponent],
  encapsulation: ViewEncapsulation.None,
})
export class FileUploadComponent {
  @Input({ required: true }) uploadType!: UploadType;
  @Output() uploadProcessed = new EventEmitter<{
    uploadedResult: JobDescriptionData | CandidateData | null;
  }>();

  readonly uploadTypeEnum = UploadType;

  selectedFile: File | null = null;
  uploadedFileDetails: JobDescriptionData | CandidateData | null = null;
  isDragging = false;
  isUploading = false;

  constructor(
    private talentMatchService: TalentMatchService,
    private destroyRef: DestroyRef,
    private toastr: ToastrService,
  ) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;

    if (input.files?.length) {
      this.setFile(input.files[0]);
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;

    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.setFile(file);
    }
  }

  clearFile() {
    this.selectedFile = null;
    this.uploadedFileDetails = null;
  }

  clearUploadedFile(shouldClear: boolean) {
    if (shouldClear) {
      this.clearFile();
    }
  }

  formatSize(bytes: number): string {
    const kb = bytes / 1024;
    return kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
  }

  onUpload() {
    if (!this.selectedFile) {
      return;
    }

    this.isUploading = true;

    this.talentMatchService
      .uploadResume(this.selectedFile, this.uploadType)
      .pipe(
        finalize(() => (this.isUploading = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (response) => {
          this.uploadedFileDetails = response.results;
          this.uploadProcessed.emit({ uploadedResult: response.results });
          this.toastr.success('Document uploaded successfully!');
        },
        error: () => {
          this.toastr.error('Failed to upload the document. Please try again.');
        },
      });
  }

  private setFile(file: File) {
    if (file.type !== 'application/pdf') {
      this.toastr.error('Please upload a PDF file.');
      return;
    }
    this.selectedFile = file;
  }
}
