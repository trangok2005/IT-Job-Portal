export default function JobsLoading() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <div className="h-8 w-56 animate-pulse rounded-lg bg-zinc-100" />
      <div className="mt-6 h-16 animate-pulse rounded-2xl bg-zinc-100" />
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-52 animate-pulse rounded-xl bg-zinc-100" />)}
      </div>
    </div>
  );
}
