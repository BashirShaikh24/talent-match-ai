import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UploadedCdDetailsComponent } from './uploaded-cd-details.component';

describe('UploadedCdDetailsComponent', () => {
  let component: UploadedCdDetailsComponent;
  let fixture: ComponentFixture<UploadedCdDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadedCdDetailsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadedCdDetailsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
