import React, { useState } from 'react';

function UserMintPage() {
  const [ethAddress, setEthAddress] = useState('');
  const [amount, setAmount] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      const res = await fetch('http://localhost:8000/user/mint-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eth_address: ethAddress, amount: parseFloat(amount) })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '신청 실패');
      setResult(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '40px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>민팅 신청</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 10 }}>
          <label>이더리움 주소<br/>
            <input value={ethAddress} onChange={e => setEthAddress(e.target.value)} required style={{ width: '100%' }} />
          </label>
        </div>
        <div style={{ marginBottom: 10 }}>
          <label>Amount (USDT)<br/>
            <input type="number" value={amount} onChange={e => setAmount(e.target.value)} required min="0.01" step="0.01" style={{ width: '100%' }} />
          </label>
        </div>
        <button type="submit">신청</button>
      </form>
      {result && <div style={{ marginTop: 20, color: 'green' }}>신청 완료!<br/>Amount: {result.amount}<br/>Address: {result.eth_address}</div>}
      {error && <div style={{ marginTop: 20, color: 'red' }}>{error}</div>}
    </div>
  );
}

export default UserMintPage; 