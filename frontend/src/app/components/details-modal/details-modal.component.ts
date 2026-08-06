import {
  ChangeDetectorRef,
  Component,
  effect,
  ElementRef,
  HostListener,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-details-modal',
  templateUrl: './details-modal.component.html',
  styleUrl: './details-modal.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class DetailsModalComponent {
  @ViewChild('modalScrollContainer') modalScrollContainer?: ElementRef<HTMLElement>;

  constructor(
    private talentMatchService: TalentMatchService,
    private cdr: ChangeDetectorRef,
  ) {
    effect(() => {
      const candidateEvaluated = this.talentMatchService.isCandidateEvaluated();

      if (candidateEvaluated && !candidateEvaluated.isMatching) {
        this.scrollModalToTop();
        this.cdr.markForCheck();
      }
    });
  }

  onBackdropClick(event: MouseEvent) {
    if ((event.target as HTMLElement).classList.contains('modal-backdrop')) {
      this.onClose();
    }
  }

  scrollModalToTop() {
    const modalScroll = this.modalScrollContainer?.nativeElement;

    if (modalScroll) {
      modalScroll.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  onClose() {
    this.talentMatchService.isModalOpen.set({
      state: false,
      selectedData: null,
      uploadedType: '',
    });
  }

  @HostListener('document:keydown.escape')
  onEscapeKey() {
    this.onClose();
  }
}
