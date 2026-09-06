export function BrandName() {
  return (
    <span className="text-lg font-bold text-primary" aria-label="IT Job Portal">
      IT <span className="text-accent">J</span>
      <span
        aria-hidden="true"
        className="mx-[0.03em] inline-flex size-[0.95em] items-center justify-center rounded-full border-[0.12em] border-accent align-[-0.08em] text-primary"
      >
        <svg viewBox="0 0 14 18" className="h-[0.68em] w-[0.54em] fill-current">
          <path d="M4 2h6L8.8 6H5.2L4 2Z" />
          <path d="m5.2 7 3.6 0 2 6.4L7 17l-3.8-3.6L5.2 7Z" />
        </svg>
      </span>
      <span className="text-accent">b</span> Portal
    </span>
  );
}
