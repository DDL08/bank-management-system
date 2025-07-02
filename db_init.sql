CREATE DATABASE IF NOT EXISTS bank_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bank_system;

-- 创建管理员表
CREATE TABLE IF NOT EXISTS admin_user (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_md5 CHAR(32) NOT NULL
);

-- 客户信息表
CREATE TABLE userInfo (
    customerID INT PRIMARY KEY AUTO_INCREMENT,
    customerName VARCHAR(50) NOT NULL,
    PID VARCHAR(18) NOT NULL UNIQUE,
    telephone VARCHAR(11) NOT NULL,
    address VARCHAR(100)
);

-- 存款类型表
CREATE TABLE deposit (
    savingID INT PRIMARY KEY AUTO_INCREMENT,
    savingName VARCHAR(50) NOT NULL,
    descrip TEXT
);

INSERT INTO deposit (savingName, descrip) VALUES
('活期', '无固定存期，可随时存取，存取金额不限的一种比较灵活的存款'),
('定活两便', '事先不约定存期，一次性存入，一次性支取的存款'),
('整存整取', '选择存款期限，整笔存入，到期提取本息，是一种定期储蓄。银行提供的存款期限有 1 年、2 年和 3 年'),
('零存整取', '一种事先约定金额，逐月按约定金额存入，到期支取本息的定期储蓄。银行提供的存款期限有 1 年、2 年和 3 年');

/*
存款类型 (deposit)包括如下属性：
1）存款编号 (savingID): 每种存款类型的唯一标识符
5
2）存款名称 (savingName): 记录存款类型的名称
3）存款描述 (descrip): 记录存款类型的描述
*/
-- 银行卡信息表
CREATE TABLE cardInfo (
    cardID CHAR(16) PRIMARY KEY,
    curID VARCHAR(10) DEFAULT 'RMB',
    openDate DATE DEFAULT CURRENT_DATE,
    openMoney DECIMAL(10,2) NOT NULL CHECK (openMoney >= 1),
    balance DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (balance >= 1),
    pass CHAR(6) NOT NULL DEFAULT '888888',
    IsReportLoss BOOLEAN DEFAULT FALSE,
    customerID INT NOT NULL,
    savingID INT NOT NULL,
    FOREIGN KEY (customerID) REFERENCES userInfo(customerID) ON DELETE CASCADE,
    FOREIGN KEY (savingID) REFERENCES deposit(savingID)
);

-- 交易记录表
CREATE TABLE tradeInfo (
    tradeID INT PRIMARY KEY AUTO_INCREMENT,
    tradeDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    tradeType ENUM('存入', '支取', '转账') NOT NULL,
    tradeMoney DECIMAL(10,2) NOT NULL CHECK (tradeMoney > 0),
    cardID CHAR(16),
    remark TEXT,
    FOREIGN KEY (cardID) REFERENCES cardInfo(cardID) ON DELETE CASCADE
);

-- 存储过程：转账
DELIMITER $$
CREATE PROCEDURE TransferMoney(
    IN fromCard CHAR(16),
    IN toCard CHAR(16),
    IN amount DECIMAL(10,2)
)
BEGIN
    START TRANSACTION;

    UPDATE cardInfo SET balance = balance - amount WHERE cardID = fromCard AND balance >= amount;
    UPDATE cardInfo SET balance = balance + amount WHERE cardID = toCard;

    INSERT INTO tradeInfo(tradeType, tradeMoney, cardID, remark)
    VALUES ('转账', amount, fromCard, CONCAT('转出给卡号: ', toCard));

    INSERT INTO tradeInfo(tradeType, tradeMoney, cardID, remark)
    VALUES ('转账', amount, toCard, CONCAT('来自卡号: ', fromCard));

    COMMIT;
END $$
DELIMITER ;

-- 触发器：开户自动插入交易记录
DELIMITER $$
CREATE TRIGGER trg_after_open_card
AFTER INSERT ON cardInfo
FOR EACH ROW
BEGIN
    INSERT INTO tradeInfo(tradeType, tradeMoney, cardID, remark)
    VALUES ('存入', NEW.openMoney, NEW.cardID, '开户初始存款');
END $$
DELIMITER ;

-- 触发器：存取款自动写入交易表
DELIMITER $$
CREATE TRIGGER trg_after_balance_update
AFTER UPDATE ON cardInfo
FOR EACH ROW
BEGIN
    IF NEW.balance > OLD.balance THEN
        INSERT INTO tradeInfo(tradeType, tradeMoney, cardID, remark)
        VALUES ('存入', NEW.balance - OLD.balance, NEW.cardID, '账户存款');
    ELSEIF NEW.balance < OLD.balance THEN
        INSERT INTO tradeInfo(tradeType, tradeMoney, cardID, remark)
        VALUES ('支取', OLD.balance - NEW.balance, NEW.cardID, '账户取款');
    END IF;
END $$
DELIMITER ;


--银行卡信息修改版本
CREATE TABLE cardInfo (
    cardID CHAR(16) PRIMARY KEY,
    curID VARCHAR(10) DEFAULT 'RMB',
    openDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    openMoney DECIMAL(10,2) NOT NULL CHECK (openMoney >= 1),
    balance DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (balance >= 1),
    pass CHAR(6) NOT NULL DEFAULT '888888',
    IsReportLoss BOOLEAN DEFAULT FALSE,
    customerID INT NOT NULL,
    savingID INT NOT NULL,
    FOREIGN KEY (customerID) REFERENCES userInfo(customerID) ON DELETE CASCADE,
    FOREIGN KEY (savingID) REFERENCES deposit(savingID)
);



--自动开卡触发器
DELIMITER $$

CREATE TRIGGER auto_create_card
AFTER INSERT ON userInfo
FOR EACH ROW
BEGIN
    DECLARE new_card_id CHAR(16);

    -- 卡号规则：固定前缀 + 8 位随机数字，确保唯一
    REPEAT
        SET new_card_id = CONCAT('10103576', LPAD(FLOOR(RAND() * 100000000), 8, '0'));
    UNTIL NOT EXISTS (SELECT 1 FROM cardInfo WHERE cardID = new_card_id)
    END REPEAT;

    -- 插入默认银行卡信息
    INSERT INTO cardInfo (
        cardID, curID, openDate, openMoney, balance, pass, IsReportLoss, customerID, savingID
    ) VALUES (
        new_card_id,          -- 自动生成的唯一卡号
        'RMB',                -- 默认币种
        NOW(),                -- 当前时间为开户日期
        100.00,               -- 默认开户金额
        100.00,               -- 初始余额
        '888888',             -- 默认密码（建议入库前改为加密）
        FALSE,                -- 默认未挂失
        NEW.customerID,       -- 刚插入的客户ID
        1                     -- 默认存款类型 savingID = 1
    );
END$$

DELIMITER ;

--卡内金额低于1元自动删卡
DELIMITER $$

CREATE TRIGGER trg_auto_close_card
AFTER UPDATE ON cardInfo
FOR EACH ROW
BEGIN
    -- 如果更新后余额小于1元，则销户（删除此卡）
    IF NEW.balance < 1 THEN
        DELETE FROM cardInfo WHERE cardID = NEW.cardID;
    END IF;
END $$

DELIMITER ;
