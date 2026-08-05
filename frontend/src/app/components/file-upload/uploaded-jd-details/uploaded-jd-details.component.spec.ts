import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UploadedJdDetailsComponent } from './uploaded-jd-details.component';

describe('UploadedJdDetailsComponent', () => {
  let component: UploadedJdDetailsComponent;
  let fixture: ComponentFixture<UploadedJdDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadedJdDetailsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadedJdDetailsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
